/**
 * API utility functions for communicating with the Nebula backend.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export interface Notebook {
  id: string;
  name: string;
  description: string;
  index_status: string;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  notebook_id: string;
  filename: string;
  file_type: string;
  status: string;
  size_bytes: number;
  created_at: string;
  processed_at: string | null;
}

export interface ChatSession {
  id: string;
  notebook_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  citations: string[];
  plan_topics: string[];
  created_at: string;
}

export class NebulaAPI {
  // Notebooks
  static async getNotebooks(): Promise<Notebook[]> {
    const res = await fetch(`${BASE_URL}/notebooks/`);
    if (!res.ok) throw new Error("Failed to fetch notebooks");
    return res.json();
  }

  static async createNotebook(name: string, description: string): Promise<Notebook> {
    const res = await fetch(`${BASE_URL}/notebooks/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description })
    });
    if (!res.ok) throw new Error("Failed to create notebook");
    return res.json();
  }

  static async getNotebook(id: string): Promise<Notebook> {
    const res = await fetch(`${BASE_URL}/notebooks/${id}`);
    if (!res.ok) throw new Error("Failed to fetch notebook");
    return res.json();
  }

  static async deleteNotebook(id: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/notebooks/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete notebook");
  }

  // Documents
  static async getDocuments(notebookId: string): Promise<Document[]> {
    const res = await fetch(`${BASE_URL}/notebooks/${notebookId}/documents/`);
    if (!res.ok) throw new Error("Failed to fetch documents");
    return res.json();
  }

  static async uploadDocument(notebookId: string, file: File): Promise<Document> {
    const formData = new FormData();
    formData.append("file", file);
    
    const res = await fetch(`${BASE_URL}/notebooks/${notebookId}/documents/`, {
      method: "POST",
      body: formData
    });
    if (!res.ok) throw new Error("Failed to upload document");
    return res.json();
  }

  static async deleteDocument(notebookId: string, documentId: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/notebooks/${notebookId}/documents/${documentId}`, {
      method: "DELETE"
    });
    if (!res.ok) throw new Error("Failed to delete document");
  }

  static async ingestUrl(notebookId: string, url: string): Promise<Document> {
    const res = await fetch(`${BASE_URL}/notebooks/${notebookId}/documents/urls`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    if (!res.ok) throw new Error("Failed to ingest URL");
    return res.json();
  }

  static async getDocumentTree(notebookId: string, documentId: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/notebooks/${notebookId}/documents/${documentId}/tree`);
    if (!res.ok) throw new Error("Failed to fetch document tree");
    return res.json();
  }

  // Chat
  static async getChatSessions(notebookId: string): Promise<ChatSession[]> {
    const res = await fetch(`${BASE_URL}/notebooks/${notebookId}/chat/sessions`);
    if (!res.ok) throw new Error("Failed to fetch chat sessions");
    return res.json();
  }

  static async createChatSession(notebookId: string): Promise<ChatSession> {
    const res = await fetch(`${BASE_URL}/notebooks/${notebookId}/chat/sessions`, {
      method: "POST"
    });
    if (!res.ok) throw new Error("Failed to create chat session");
    return res.json();
  }

  static async getChatMessages(notebookId: string, sessionId: string): Promise<ChatMessage[]> {
    const res = await fetch(`${BASE_URL}/notebooks/${notebookId}/chat/sessions/${sessionId}/messages`);
    if (!res.ok) throw new Error("Failed to fetch chat messages");
    return res.json();
  }

  static async sendMessage(notebookId: string, sessionId: string, content: string): Promise<ChatMessage> {
    const res = await fetch(`${BASE_URL}/notebooks/${notebookId}/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content })
    });
    if (!res.ok) throw new Error("Failed to send message");
    return res.json();
  }
}
