"""LangGraph agent pipeline: plan -> fetch -> write.

Orchestrates the multi-step RAG process using LangGraph's state-machine
model for reliable, observable AI reasoning.
"""

import logging
from typing import Any, TypedDict
from langgraph.graph import StateGraph, START, END
from app.llm_provider import get_async_client
from app.agent.prompts import PLAN_SYSTEM_PROMPT, WRITE_SYSTEM_PROMPT, GRADE_DOCUMENTS_PROMPT, REWRITE_PLAN_PROMPT
from app.rag.engine import retrieve_from_notebook
from app.config import settings


class AgentState(TypedDict):
    """State schema for the LangGraph agent."""

    user_query: str
    notebook_id: str
    session_id: str
    plan_topics: list[str]
    retrieved_context: list[dict[str, Any]]
    response: str
    citations: list[str]
    iteration_count: int
    documents_relevant: str



async def plan_node(state: AgentState) -> AgentState:
    """Extract search topics from the user's query using the LLM."""
    client = get_async_client()
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": PLAN_SYSTEM_PROMPT},
                {"role": "user", "content": state["user_query"]}
            ],
            temperature=0,
        )
        content = response.choices[0].message.content or ""
        
        topics = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("-"):
                topics.append(line)
            elif line.startswith("-"):
                topics.append(line[1:].strip())
                
        # Filter NONE
        topics = [t for t in topics if t.upper() != "NONE"]
        
        return {"plan_topics": topics}
    except Exception as e:
        logging.getLogger(__name__).exception(f"Plan error: {e}")
        return {"plan_topics": []}


async def fetch_node(state: AgentState) -> AgentState:
    """Retrieve relevant context from the notebook's PageIndex tree."""
    if not state.get("plan_topics"):
        return {"retrieved_context": []}
        
    context = await retrieve_from_notebook(state["notebook_id"], state["plan_topics"])
    return {"retrieved_context": context}


async def write_node(state: AgentState) -> AgentState:
    """Generate a grounded response using the retrieved context."""
    # If we hit max iterations and still didn't find anything
    if state.get("iteration_count", 0) >= 3 and state.get("documents_relevant") == "no":
        return {
            "response": "I searched multiple times but couldn't find enough information in your notebook to answer this question. Try uploading more relevant documents.",
            "citations": []
        }

    client = get_async_client()
    
    # Build context string
    context_str = ""
    for idx, ctx in enumerate(state.get("retrieved_context", [])):
        context_str += f"Source [{idx+1}]: {ctx.get('source_filename', 'Unknown')} - {ctx.get('section_path', 'Unknown')}\n"
        context_str += f"{ctx.get('content', '')}\n\n"
        
    prompt = f"User Query: {state['user_query']}\n\nContext Passages:\n{context_str}"
    
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": WRITE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        
        # Simple citation extraction using regex for [Source: filename - section]
        import re
        citations = re.findall(r'\[Source:\s*.*?\]', content)
        
        return {"response": content, "citations": citations}
    except Exception as e:
        logging.getLogger(__name__).exception(f"Write error: {e}")
        return {"response": "Error generating response.", "citations": []}


async def grade_documents(state: AgentState) -> AgentState:
    """Evaluate if retrieved context is relevant."""
    client = get_async_client()
    context_str = "\n\n".join([ctx.get('content', '') for ctx in state.get("retrieved_context", [])])
    
    if not context_str.strip():
        return {"documents_relevant": "no", "iteration_count": state.get("iteration_count", 0) + 1}
        
    prompt = f"User Query: {state['user_query']}\n\nContext Passage:\n{context_str}"
    
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": GRADE_DOCUMENTS_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
        )
        grade = response.choices[0].message.content.strip().lower()
        if "yes" in grade:
            grade = "yes"
        else:
            grade = "no"
            
        return {"documents_relevant": grade, "iteration_count": state.get("iteration_count", 0) + 1}
    except Exception as e:
        logging.getLogger(__name__).exception(f"Grade error: {e}")
        return {"documents_relevant": "no", "iteration_count": state.get("iteration_count", 0) + 1}


async def rewrite_plan(state: AgentState) -> AgentState:
    """Rewrite search topics if previous fetch failed."""
    client = get_async_client()
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": REWRITE_PLAN_PROMPT},
                {"role": "user", "content": f"User Query: {state['user_query']}\nPrevious Topics: {', '.join(state.get('plan_topics', []))}"}
            ],
            temperature=0.5,
        )
        content = response.choices[0].message.content or ""
        
        topics = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("-"):
                topics.append(line)
            elif line.startswith("-"):
                topics.append(line[1:].strip())
                
        return {"plan_topics": topics}
    except Exception as e:
        logging.getLogger(__name__).exception(f"Rewrite error: {e}")
        return {"plan_topics": state.get("plan_topics", [])}


def decide_to_generate(state: AgentState) -> str:
    """Conditional edge logic after grading."""
    if state.get("documents_relevant") == "yes":
        return "write"
    
    # If no and we haven't hit limit, rewrite
    if state.get("iteration_count", 0) < 3:
        return "rewrite_plan"
        
    # We hit limit, give up and generate fallback response
    return "write"


def build_graph() -> Any:
    """Build and compile the LangGraph state machine."""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("plan", plan_node)
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("rewrite_plan", rewrite_plan)
    workflow.add_node("write", write_node)
    
    workflow.add_edge(START, "plan")
    workflow.add_edge("plan", "fetch")
    workflow.add_edge("fetch", "grade_documents")
    
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "write": "write",
            "rewrite_plan": "rewrite_plan"
        }
    )
    
    workflow.add_edge("rewrite_plan", "fetch")
    workflow.add_edge("write", END)
    
    return workflow.compile()
