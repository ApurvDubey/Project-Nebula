"use client";

import React, { useState, useEffect } from 'react';
import { Headphones, Loader2, PlayCircle } from 'lucide-react';
import { NebulaAPI } from '@/lib/api';

export default function PodcastPanel({ notebookId }: { notebookId: string }) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [podcastUrl, setPodcastUrl] = useState<string | null>(null);

  const checkPodcastStatus = async () => {
    try {
      // Just try to fetch the headers to see if it 404s
      const url = NebulaAPI.getPodcastUrl(notebookId);
      const res = await fetch(url, { method: 'HEAD' });
      if (res.ok) {
        setPodcastUrl(url);
        setIsGenerating(false);
      }
    } catch (err) {
      // Not ready yet
    }
  };

  useEffect(() => {
    checkPodcastStatus();
    if (isGenerating) {
      const interval = setInterval(checkPodcastStatus, 5000);
      return () => clearInterval(interval);
    }
  }, [notebookId, isGenerating]);

  const handleGenerate = async () => {
    try {
      setIsGenerating(true);
      await NebulaAPI.generatePodcast(notebookId);
    } catch (err) {
      console.error(err);
      setIsGenerating(false);
      alert("Failed to start podcast generation.");
    }
  };

  return (
    <div className="bg-surface/50 border border-white/5 p-4 rounded-2xl flex flex-col gap-4">
      <div className="flex items-center gap-2 text-gray-300 font-semibold">
        <Headphones size={20} className="text-primary-400" />
        <h2>Audio Overview</h2>
      </div>
      
      {podcastUrl ? (
        <div className="flex flex-col gap-3">
          <audio controls src={podcastUrl} className="w-full" />
          <button 
            onClick={handleGenerate}
            className="text-xs text-primary-400 hover:text-primary-300 text-left transition-colors"
          >
            Regenerate Podcast
          </button>
        </div>
      ) : isGenerating ? (
        <div className="flex items-center gap-3 text-sm text-gray-400 p-4 bg-black/20 rounded-xl">
          <Loader2 size={16} className="animate-spin text-primary-500" />
          <span>Synthesizing podcast audio... This may take a few minutes.</span>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-gray-400">
            Generate an engaging two-host podcast summarizing the context of this notebook.
          </p>
          <button 
            onClick={handleGenerate}
            className="flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-500 text-white p-3 rounded-xl transition-colors text-sm font-medium"
          >
            <PlayCircle size={18} />
            Generate Audio Overview
          </button>
        </div>
      )}
    </div>
  );
}
