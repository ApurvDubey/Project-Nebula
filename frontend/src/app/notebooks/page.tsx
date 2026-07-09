"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Book, Plus, ArrowRight, Loader2, Database } from 'lucide-react';
import { NebulaAPI, Notebook } from '@/lib/api';

export default function NotebooksPage() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [newNotebookName, setNewNotebookName] = useState("");

  useEffect(() => {
    fetchNotebooks();
  }, []);

  const fetchNotebooks = async () => {
    try {
      const data = await NebulaAPI.getNotebooks();
      setNotebooks(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNotebookName.trim() || isCreating) return;
    
    setIsCreating(true);
    try {
      await NebulaAPI.createNotebook(newNotebookName.trim(), "");
      setNewNotebookName("");
      await fetchNotebooks();
    } catch (err) {
      console.error(err);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="min-h-screen p-8 max-w-6xl mx-auto animate-fade-in">
      <header className="flex justify-between items-end mb-12">
        <div>
          <h1 className="text-4xl font-display font-bold mb-2">Your Notebooks</h1>
          <p className="text-gray-400">Manage your private document collections</p>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Create New Card */}
        <div className="glass-panel rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="w-12 h-12 bg-primary-600/20 text-primary-500 rounded-xl flex items-center justify-center mb-4">
              <Plus size={24} />
            </div>
            <h3 className="text-xl font-semibold mb-2">Create Notebook</h3>
            <p className="text-sm text-gray-400 mb-6">Start a new collection for a project, research, or personal knowledge.</p>
          </div>
          
          <form onSubmit={handleCreate} className="flex gap-2">
            <input
              type="text"
              value={newNotebookName}
              onChange={e => setNewNotebookName(e.target.value)}
              placeholder="e.g. Physics 101"
              className="flex-1 bg-surface-hover border border-white/10 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-primary-500/50"
            />
            <button 
              type="submit"
              disabled={!newNotebookName.trim() || isCreating}
              className="bg-primary-600 hover:bg-primary-500 disabled:opacity-50 px-4 py-2 rounded-lg font-medium transition-colors flex items-center"
            >
              {isCreating ? <Loader2 size={18} className="animate-spin" /> : "Create"}
            </button>
          </form>
        </div>

        {/* List Notebooks */}
        {isLoading ? (
          <div className="col-span-1 md:col-span-2 flex items-center justify-center p-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
          </div>
        ) : (
          notebooks.map(nb => (
            <Link 
              href={`/notebooks/${nb.id}`} 
              key={nb.id}
              className="glass-card rounded-2xl p-6 flex flex-col group cursor-pointer"
            >
              <div className="w-12 h-12 bg-surface text-gray-300 rounded-xl flex items-center justify-center mb-4 group-hover:bg-primary-600 group-hover:text-white transition-colors">
                <Database size={24} />
              </div>
              <h3 className="text-xl font-semibold mb-2">{nb.name}</h3>
              <p className="text-sm text-gray-400 mb-6 flex-1">
                {nb.description || "No description provided."}
              </p>
              
              <div className="flex items-center justify-between text-sm text-gray-500 mt-auto pt-4 border-t border-white/5">
                <span>{new Date(nb.created_at).toLocaleDateString()}</span>
                <span className="flex items-center text-primary-400 font-medium group-hover:translate-x-1 transition-transform">
                  Open <ArrowRight size={16} className="ml-1" />
                </span>
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
