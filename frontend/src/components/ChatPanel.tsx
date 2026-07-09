"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader2, Info } from 'lucide-react';
import { NebulaAPI, ChatMessage } from '@/lib/api';

export default function ChatPanel({ notebookId }: { notebookId: string }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize session
  useEffect(() => {
    const initSession = async () => {
      try {
        const sessions = await NebulaAPI.getChatSessions(notebookId);
        if (sessions.length > 0) {
          const sid = sessions[0].id;
          setSessionId(sid);
          const msgs = await NebulaAPI.getChatMessages(notebookId, sid);
          setMessages(msgs);
        } else {
          const session = await NebulaAPI.createChatSession(notebookId);
          setSessionId(session.id);
        }
      } catch (err) {
        console.error("Failed to init chat session", err);
      }
    };
    initSession();
  }, [notebookId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !sessionId || isSending) return;

    const userMsg = input.trim();
    setInput("");
    
    // Optimistic UI for user message
    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: userMsg,
      citations: [],
      plan_topics: [],
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);
    setIsSending(true);

    try {
      // Backend actually inserts the user message and returns the assistant message
      const assistantMsg = await NebulaAPI.sendMessage(notebookId, sessionId, userMsg);
      // We should ideally fetch all messages again to get proper IDs, but appending works for now
      setMessages(prev => {
        // Remove the temp message and fetch from server (or just append)
        return [...prev, assistantMsg];
      });
      
      // Let's just fetch all messages to be safe and get correct IDs
      const freshMsgs = await NebulaAPI.getChatMessages(notebookId, sessionId);
      setMessages(freshMsgs);
    } catch (err) {
      console.error("Failed to send message", err);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface/30 backdrop-blur-md rounded-2xl border border-white/10 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-white/10 bg-surface/50">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Bot className="text-primary-500" />
          Nebula Assistant
        </h2>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.length === 0 && !isSending && (
          <div className="h-full flex flex-col items-center justify-center text-gray-500 gap-4">
            <Bot className="w-16 h-16 opacity-50" />
            <p>Ask a question about your documents!</p>
          </div>
        )}
        
        {messages.map((msg, i) => (
          <div key={msg.id || i} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
              msg.role === 'user' ? 'bg-primary-600' : 'bg-surface border border-white/10'
            }`}>
              {msg.role === 'user' ? <User size={20} /> : <Bot size={20} className="text-primary-400" />}
            </div>
            
            <div className={`max-w-[80%] flex flex-col gap-2 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`p-4 rounded-2xl ${
                msg.role === 'user' 
                  ? 'bg-primary-600/90 text-white rounded-tr-sm' 
                  : 'bg-surface/80 border border-white/10 rounded-tl-sm'
              }`}>
                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              </div>
              
              {/* Citations/Topics */}
              {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-1">
                  {msg.citations.map((cite, idx) => (
                    <span key={idx} className="text-xs px-2 py-1 bg-surface-hover border border-white/5 rounded-md text-gray-400 flex items-center gap-1">
                      <Info size={12} />
                      {cite.replace(/\[|\]/g, '')}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        
        {isSending && (
          <div className="flex gap-4">
            <div className="w-10 h-10 rounded-full bg-surface border border-white/10 flex items-center justify-center shrink-0">
              <Bot size={20} className="text-primary-400" />
            </div>
            <div className="p-4 rounded-2xl bg-surface/80 border border-white/10 rounded-tl-sm flex items-center gap-3 text-gray-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              Thinking...
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSend} className="p-4 bg-surface/50 border-t border-white/10">
        <div className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            disabled={isSending || !sessionId}
            placeholder="Ask about your documents..."
            className="w-full bg-surface-hover border border-white/10 rounded-xl px-6 py-4 pr-16 focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/50 transition-all text-white placeholder-gray-500"
          />
          <button
            type="submit"
            disabled={!input.trim() || isSending || !sessionId}
            className="absolute right-2 p-3 bg-primary-600 text-white rounded-lg hover:bg-primary-500 disabled:opacity-50 disabled:hover:bg-primary-600 transition-colors"
          >
            <Send size={18} className={isSending ? 'opacity-0' : 'opacity-100'} />
            {isSending && <Loader2 size={18} className="absolute inset-0 m-auto animate-spin" />}
          </button>
        </div>
      </form>
    </div>
  );
}
