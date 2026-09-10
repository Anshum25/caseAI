"use client";

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';

type Status = 'uploading' | 'processing_scanned_pages' | 'extracting_case_information' | 'creating_searchable_index' | 'generating_summary' | 'ready' | 'failed' | 'not_found';

// ─── Upload New PDF Modal ────────────────────────────────────────────────────
function UploadModal({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadFile = async (file: File) => {
    if (file.type !== 'application/pdf') {
      setUploadError('Only PDF files are supported.');
      return;
    }
    setUploadError('');
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/documents/upload', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      router.push(`/case/${data.document_id}`);
    } catch {
      setUploadError('Upload failed. Make sure the backend is running.');
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setIsDragging(true);
    else setIsDragging(false);
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files?.[0]) await uploadFile(e.dataTransfer.files[0]);
  }, []);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) await uploadFile(e.target.files[0]);
  };

  // Close on backdrop click
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden animate-in">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Upload New PDF</h2>
            <p className="text-xs text-gray-500 mt-0.5">Start a fresh case analysis</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-700"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Drop Zone */}
        <div className="p-6">
          <div
            className={`relative rounded-xl border-2 border-dashed p-10 text-center transition-all duration-200 cursor-pointer ${
              isDragging
                ? 'border-blue-500 bg-blue-50 scale-[1.01]'
                : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".pdf"
              onChange={handleFileChange}
            />

            {uploading ? (
              <div className="flex flex-col items-center gap-3">
                <svg className="w-10 h-10 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <p className="text-sm font-medium text-blue-600">Uploading & processing…</p>
                <p className="text-xs text-gray-400">You'll be redirected automatically</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className={`p-4 rounded-full transition-colors ${isDragging ? 'bg-blue-100' : 'bg-gray-100'}`}>
                  <svg className={`w-8 h-8 transition-colors ${isDragging ? 'text-blue-500' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-700">
                    {isDragging ? 'Drop it here!' : 'Drag & drop your PDF'}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">or click to browse files</p>
                </div>
                <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-600 text-white text-xs font-medium rounded-full hover:bg-blue-700 transition-colors">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Select PDF
                </span>
              </div>
            )}
          </div>

          {uploadError && (
            <p className="mt-3 text-xs text-red-500 flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {uploadError}
            </p>
          )}

          <p className="mt-4 text-center text-xs text-gray-400">
            Supported format: <span className="font-medium text-gray-500">PDF</span> · Max size: 50 MB
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Main Dashboard ──────────────────────────────────────────────────────────
export default function CaseDashboard({ documentId }: { documentId: string }) {
  const [status, setStatus] = useState<Status>('uploading');
  const [progress, setProgress] = useState(0);
  const [summary, setSummary] = useState<any>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/documents/${documentId}/status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data.status);
        setProgress(data.progress);
        
        if (data.status === 'ready' && !summary) {
          fetchSummary();
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchSummary = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/documents/${documentId}/summary`);
      if (res.ok) {
        const data = await res.json();
        setSummary(data.summary);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (status !== 'ready' && status !== 'failed' && status !== 'not_found') {
      interval = setInterval(fetchStatus, 2000);
    }
    return () => clearInterval(interval);
  }, [status]);

  if (status === 'failed' || status === 'not_found') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="p-8 text-red-500 text-center">Error processing document.</div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Try Another PDF
        </button>
        {showUploadModal && <UploadModal onClose={() => setShowUploadModal(false)} />}
      </div>
    );
  }

  if (status !== 'ready') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <h2 className="text-2xl font-semibold mb-4">Processing Document...</h2>
        <div className="w-64 bg-gray-200 rounded-full h-2.5 mb-4">
          <div className="bg-blue-600 h-2.5 rounded-full transition-all duration-500" style={{ width: `${progress}%` }}></div>
        </div>
        <p className="text-gray-500 uppercase text-sm tracking-wider">{status.replace(/_/g, ' ')}</p>
      </div>
    );
  }

  return (
    <>
      {showUploadModal && <UploadModal onClose={() => setShowUploadModal(false)} />}

      <div className="flex flex-col h-screen overflow-hidden">
        <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-800">NyayaAI - Case Workspace</h1>
          <div className="flex items-center gap-3">
            {/* Upload New PDF Button */}
            <button
              onClick={() => setShowUploadModal(true)}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 hover:border-blue-400 transition-all duration-150"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              New PDF
            </button>
          </div>
        </header>
        
        <div className="flex-1 overflow-hidden bg-gray-50 p-6 flex gap-6">
          {/* Left Side: Summary */}
          <div className="w-1/2 overflow-auto bg-white p-6 rounded-lg shadow-sm border">
            <h2 className="text-xl font-bold border-b pb-4 mb-4 text-gray-800">Case Summary</h2>
            {summary ? (
              <div className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">
                {typeof summary === 'string' ? summary : JSON.stringify(summary, null, 2)}
              </div>
            ) : (
              <p>Loading summary...</p>
            )}
          </div>

          {/* Right Side: Chat */}
          <div className="w-1/2 bg-white p-6 rounded-lg shadow-sm border flex flex-col overflow-hidden">
            <h2 className="text-xl font-bold border-b pb-4 mb-4 text-gray-800">Chat with Document</h2>
            <div className="flex-1 overflow-hidden">
              <ChatInterface documentId={documentId} />
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function ChatInterface({ documentId }: { documentId: string }) {
  const [messages, setMessages] = useState<{role: string, content: string, citations?: any[]}[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/documents/${documentId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: userMessage })
      });
      
      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, { role: "ai", content: data.answer, citations: data.citations }]);
      } else {
        throw new Error("Chat failed");
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: "ai", content: "Sorry, an error occurred while fetching the answer." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto mb-4 space-y-4 pr-2">
        {messages.map((m, i) => (
          <div key={i} className={`p-4 rounded-lg ${m.role === 'user' ? 'bg-blue-50 ml-12' : 'bg-gray-100 mr-12'}`}>
            <p className="font-semibold mb-1 text-sm text-gray-500">{m.role === 'user' ? 'You' : 'NyayaAI'}</p>
            <p className="text-gray-800 whitespace-pre-wrap">{m.content}</p>
            {m.citations && m.citations.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-xs font-semibold text-gray-500 mb-2">SOURCES:</p>
                <div className="flex flex-wrap gap-2">
                  {m.citations.map((c: any, idx: number) => (
                    <a 
                      key={idx} 
                      href={`http://127.0.0.1:8000/api/documents/${documentId}/pages/${c.page}`} 
                      target="_blank" 
                      rel="noreferrer"
                      className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded hover:bg-blue-200 transition-colors cursor-pointer"
                    >
                      [p. {c.page}]
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
        {loading && <div className="p-4 bg-gray-100 rounded-lg mr-12 text-gray-500 animate-pulse">Thinking...</div>}
      </div>
      <form onSubmit={sendMessage} className="flex gap-2">
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything about this case..." 
          className="flex-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button type="submit" disabled={loading} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
          Send
        </button>
      </form>
    </div>
  );
}
