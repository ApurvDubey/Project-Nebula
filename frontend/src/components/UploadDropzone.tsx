"use client";

import React, { useCallback, useState } from 'react';
import { UploadCloud, File, CheckCircle, AlertCircle, Loader2, Link as LinkIcon } from 'lucide-react';
import { NebulaAPI } from '@/lib/api';

export default function UploadDropzone({ notebookId, onUploadComplete }: { notebookId: string, onUploadComplete: () => void }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [urlInput, setUrlInput] = useState("");

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragging(true);
    } else if (e.type === "dragleave") {
      setIsDragging(false);
    }
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  }, [notebookId]);

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      await uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file: File) => {
    setIsUploading(true);
    setError(null);
    setSuccess(null);
    try {
      await NebulaAPI.uploadDocument(notebookId, file);
      setSuccess(`${file.name} uploaded successfully!`);
      onUploadComplete();
    } catch (err: any) {
      setError(err.message || "Failed to upload file");
    } finally {
      setIsUploading(false);
      setTimeout(() => setSuccess(null), 3000);
    }
  };

  return (
    <div className="w-full">
      <div 
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`relative flex flex-col items-center justify-center w-full h-48 border-2 border-dashed rounded-2xl transition-all duration-300 ${
          isDragging 
            ? 'border-primary-500 bg-primary-500/10' 
            : 'border-white/20 bg-surface/30 hover:border-white/40 hover:bg-surface/50'
        }`}
      >
        <input 
          type="file"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          onChange={handleChange}
          disabled={isUploading}
          accept=".pdf,.docx,.txt,.md"
        />
        
        <div className="flex flex-col items-center justify-center p-6 text-center pointer-events-none">
          {isUploading ? (
            <Loader2 className="w-12 h-12 text-primary-500 animate-spin mb-4" />
          ) : (
            <UploadCloud className={`w-12 h-12 mb-4 transition-colors ${isDragging ? 'text-primary-500' : 'text-gray-400'}`} />
          )}
          
          <h3 className="text-xl font-semibold mb-2">
            {isUploading ? "Uploading..." : "Click or drag document to upload"}
          </h3>
          <p className="text-sm text-gray-400">
            Supports PDF, DOCX, TXT, and Markdown files
          </p>
        </div>
      </div>

      {/* URL Ingestion Field */}
      <div className="mt-4 flex gap-2">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <LinkIcon className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="url"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            disabled={isUploading}
            placeholder="Or paste a website URL to ingest..."
            className="w-full pl-10 pr-4 py-3 bg-surface/30 border-2 border-white/10 rounded-xl focus:border-primary-500 focus:outline-none transition-colors"
          />
        </div>
        <button
          onClick={async () => {
            if (!urlInput) return;
            setIsUploading(true);
            setError(null);
            setSuccess(null);
            try {
              await NebulaAPI.ingestUrl(notebookId, urlInput);
              setSuccess(`URL ingested successfully!`);
              setUrlInput("");
              onUploadComplete();
            } catch (err: any) {
              setError(err.message || "Failed to ingest URL");
            } finally {
              setIsUploading(false);
              setTimeout(() => setSuccess(null), 3000);
            }
          }}
          disabled={!urlInput || isUploading}
          className="px-6 py-3 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl font-semibold transition-colors"
        >
          Ingest
        </button>
      </div>

      {/* Status Messages */}
      {error && (
        <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400 animate-fade-in">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p>{error}</p>
        </div>
      )}
      {success && (
        <div className="mt-4 p-4 bg-green-500/10 border border-green-500/20 rounded-xl flex items-center gap-3 text-green-400 animate-fade-in">
          <CheckCircle className="w-5 h-5 shrink-0" />
          <p>{success}</p>
        </div>
      )}
    </div>
  );
}
