"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { ChevronLeft, FileText, Trash2, Loader2 } from 'lucide-react';
import { NebulaAPI, Notebook, Document } from '@/lib/api';
import UploadDropzone from '@/components/UploadDropzone';
import ChatPanel from '@/components/ChatPanel';
import DocumentGraph from '@/components/DocumentGraph';
import { useParams } from 'next/navigation';

export default function NotebookView() {
  const params = useParams();
  const notebookId = params.id as string;
  
  const [notebook, setNotebook] = useState<Notebook | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [graphModalDoc, setGraphModalDoc] = useState<string | null>(null);

  const fetchNotebookData = async () => {
    try {
      const nb = await NebulaAPI.getNotebook(notebookId);
      setNotebook(nb);
      const docs = await NebulaAPI.getDocuments(notebookId);
      setDocuments(docs);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNotebookData();
    // Simple polling for document status updates
    const interval = setInterval(fetchNotebookData, 5000);
    return () => clearInterval(interval);
  }, [notebookId]);

  const handleDeleteDoc = async (docId: string) => {
    if (!confirm("Are you sure you want to delete this document?")) return;
    try {
      await NebulaAPI.deleteDocument(notebookId, docId);
      fetchNotebookData();
    } catch (err) {
      console.error(err);
    }
  };

  if (isLoading && !notebook) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!notebook) return <div className="p-8 text-center">Notebook not found.</div>;

  return (
    <div className="h-screen max-h-screen flex flex-col p-4 md:p-8 max-w-7xl mx-auto animate-fade-in gap-6">
      <header className="flex items-center gap-4 shrink-0">
        <Link href="/notebooks" className="p-2 bg-surface hover:bg-surface-hover border border-white/10 rounded-lg transition-colors">
          <ChevronLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold">{notebook.name}</h1>
          <p className="text-sm text-gray-400">
            {documents.length} document{documents.length !== 1 ? 's' : ''} in notebook
          </p>
        </div>
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
        {/* Left Column: Documents */}
        <div className="col-span-1 flex flex-col gap-6 overflow-hidden">
          <div className="shrink-0">
            <UploadDropzone notebookId={notebookId} onUploadComplete={fetchNotebookData} />
          </div>
          
          <div className="flex-1 glass-panel rounded-2xl p-4 overflow-y-auto">
            <h3 className="font-semibold mb-4 text-gray-300">Documents</h3>
            <div className="space-y-3">
              {documents.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-8">No documents uploaded yet.</p>
              ) : (
                documents.map(doc => (
                  <div key={doc.id} className="bg-surface/50 border border-white/5 p-3 rounded-xl flex items-center gap-3 group">
                    <div className={`p-2 rounded-lg shrink-0 ${
                      doc.status === 'ready' ? 'bg-green-500/10 text-green-500' :
                      doc.status === 'failed' ? 'bg-red-500/10 text-red-500' :
                      'bg-yellow-500/10 text-yellow-500'
                    }`}>
                      <FileText size={18} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate" title={doc.filename}>{doc.filename}</p>
                      <p className="text-xs text-gray-500 capitalize flex items-center gap-1">
                        {doc.status}
                        {(doc.status === 'pending' || doc.status === 'processing') && (
                          <Loader2 size={10} className="animate-spin" />
                        )}
                      </p>
                    </div>
                    {doc.status === 'ready' && (
                      <button 
                        onClick={() => setGraphModalDoc(doc.id)}
                        className="px-2 py-1 text-xs bg-primary-600 hover:bg-primary-500 rounded-md transition-colors opacity-0 group-hover:opacity-100"
                      >
                        View Graph
                      </button>
                    )}
                    <button 
                      onClick={() => handleDeleteDoc(doc.id)}
                      className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Chat */}
        <div className="col-span-1 lg:col-span-2 h-full">
          <ChatPanel notebookId={notebookId} />
        </div>
      </div>

      {/* Graph Modal */}
      {graphModalDoc && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 lg:p-12 animate-fade-in">
          <div className="bg-surface border border-white/10 rounded-2xl w-full h-full max-h-full flex flex-col overflow-hidden">
            <div className="flex justify-between items-center p-4 border-b border-white/10 shrink-0">
              <h2 className="text-xl font-bold">Document Knowledge Graph</h2>
              <button 
                onClick={() => setGraphModalDoc(null)}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
            <div className="flex-1 overflow-hidden p-4">
              <DocumentGraph notebookId={notebookId} documentId={graphModalDoc} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
