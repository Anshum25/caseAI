"use client";

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import MarkdownRenderer from '../ui/MarkdownRenderer';

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
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/documents/upload`, {
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

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm transition-all"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden border border-slate-100">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Upload New Case Document</h2>
            <p className="text-xs text-slate-500 mt-0.5">PDF files up to 50 MB are supported</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-200/60 transition-colors text-slate-400 hover:text-slate-700"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6">
          <div
            className={`relative rounded-xl border-2 border-dashed p-10 text-center transition-all duration-200 cursor-pointer ${
              isDragging
                ? 'border-blue-500 bg-blue-50/80 scale-[1.01]'
                : 'border-slate-300 hover:border-blue-500 hover:bg-slate-50'
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
              <div className="flex flex-col items-center gap-3 py-2">
                <svg className="w-10 h-10 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <p className="text-sm font-semibold text-blue-700">Uploading & Analyzing PDF...</p>
                <p className="text-xs text-slate-400">Extracting text & running AI models</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className={`p-4 rounded-full transition-colors ${isDragging ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-500'}`}>
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-800">
                    {isDragging ? 'Drop your PDF here' : 'Drag & drop legal PDF'}
                  </p>
                  <p className="text-xs text-slate-400 mt-1">or click to browse local files</p>
                </div>
                <span className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-full shadow-xs hover:bg-blue-700 transition-colors">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Browse PDF File
                </span>
              </div>
            )}
          </div>

          {uploadError && (
            <p className="mt-3 text-xs text-red-600 bg-red-50 p-2.5 rounded-lg border border-red-100 flex items-center gap-1.5">
              <svg className="w-4 h-4 text-red-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {uploadError}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function CaseDashboard({ documentId }: { documentId: string }) {
  const [status, setStatus] = useState<Status>('uploading');
  const [progress, setProgress] = useState(0);
  const [summary, setSummary] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<any>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);

  const fetchDocument = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/documents/${documentId}`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data.status);
        setProgress(data.progress || 100);
        
        if (data.status === 'ready') {
          setSummary(data.summary);
          setMetadata(data.metadata);
        }
      } else if (res.status === 404) {
        setStatus('not_found');
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchDocument();
    
    let interval: NodeJS.Timeout;
    if (status !== 'ready' && status !== 'failed' && status !== 'not_found') {
      interval = setInterval(fetchDocument, 2000);
    }
    return () => clearInterval(interval);
  }, [documentId, status]);

  if (status === 'failed' || status === 'not_found') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 gap-4 p-6">
        <div className="p-8 bg-white border border-red-200 rounded-2xl shadow-sm text-center max-w-md">
          <div className="w-12 h-12 bg-red-50 text-red-500 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-lg font-bold text-slate-900">Document Processing Failed</h3>
          <p className="text-xs text-slate-500 mt-1">We couldn't parse text from this PDF. Please verify the document format and try again.</p>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 shadow-sm transition-all"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Upload Another PDF
        </button>
        {showUploadModal && <UploadModal onClose={() => setShowUploadModal(false)} />}
      </div>
    );
  }

  if (status !== 'ready') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 p-6">
        <div className="bg-white border border-slate-200/80 rounded-2xl shadow-sm p-8 max-w-md w-full text-center">
          <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4 animate-bounce">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mb-1">Analyzing Document...</h2>
          <p className="text-xs text-slate-500 mb-6 uppercase tracking-wider font-semibold">
            {status.replace(/_/g, ' ')}
          </p>
          <div className="w-full bg-slate-100 rounded-full h-3 mb-2 overflow-hidden">
            <div
              className="bg-blue-600 h-full rounded-full transition-all duration-500 shadow-xs"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <div className="flex justify-between text-xs text-slate-400 font-medium">
            <span>Progress</span>
            <span>{progress}%</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      {showUploadModal && <UploadModal onClose={() => setShowUploadModal(false)} />}

      <div className="flex flex-col h-screen overflow-hidden bg-slate-100/60">
        {/* Workspace Top Header */}
        <header className="bg-white border-b border-slate-200 px-6 py-3.5 flex items-center justify-between shadow-2xs z-10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-blue-600 text-white font-bold rounded-xl flex items-center justify-center shadow-sm text-sm">
              N
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-900 leading-tight">NyayaAI — Case Workspace</h1>
              <p className="text-[11px] text-slate-500">Legal Intelligence & Automated Case Analysis</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/history"
              className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-all shadow-2xs"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              View History
            </Link>
            <button
              onClick={() => setShowUploadModal(true)}
              className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200/80 rounded-xl hover:bg-blue-100/70 transition-all shadow-2xs"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Upload New PDF
            </button>
          </div>
        </header>

        {/* Main Split Layout */}
        <div className="flex-1 overflow-hidden p-5 flex gap-5">
          {/* Left Panel: Case Summary & Metadata */}
          <div className="w-1/2 overflow-y-auto bg-white p-6 rounded-2xl shadow-xs border border-slate-200/80 flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3.5 mb-5">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h2 className="text-lg font-bold text-slate-900">Case Summary</h2>
              </div>
              <span className="text-xs font-medium text-slate-400 bg-slate-50 px-2.5 py-1 rounded-md border border-slate-100">
                Auto-Generated
              </span>
            </div>

            {/* Structured Metadata Card Header */}
            {metadata && Object.keys(metadata).length > 0 && (
              <div className="mb-6 p-4 bg-slate-50/80 border border-slate-200/90 rounded-xl space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/80 pb-2.5">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-md">
                      {metadata.case_type || 'Legal Document'}
                    </span>
                    <h3 className="text-sm font-bold text-slate-900 mt-1">
                      {metadata.case_number ? `Case No: ${metadata.case_number}` : 'Extracted Case Details'} {metadata.case_year ? `(${metadata.case_year})` : ''}
                    </h3>
                  </div>
                  {metadata.outcome && (
                    <span className="text-xs font-semibold px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg">
                      {metadata.outcome}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  {metadata.court && (
                    <div>
                      <span className="font-semibold text-slate-400 text-[10px] uppercase tracking-wider block">Court</span>
                      <span className="font-semibold text-slate-800">{metadata.court}</span>
                    </div>
                  )}
                  {metadata.judges && metadata.judges.length > 0 && (
                    <div>
                      <span className="font-semibold text-slate-400 text-[10px] uppercase tracking-wider block">Bench / Judge</span>
                      <span className="font-medium text-slate-800">{metadata.judges.join(', ')}</span>
                    </div>
                  )}
                  {metadata.petitioners && metadata.petitioners.length > 0 && (
                    <div>
                      <span className="font-semibold text-slate-400 text-[10px] uppercase tracking-wider block">Petitioner(s)</span>
                      <span className="text-slate-700">{metadata.petitioners.join(', ')}</span>
                    </div>
                  )}
                  {metadata.respondents && metadata.respondents.length > 0 && (
                    <div>
                      <span className="font-semibold text-slate-400 text-[10px] uppercase tracking-wider block">Respondent(s)</span>
                      <span className="text-slate-700">{metadata.respondents.join(', ')}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Markdown Case Summary */}
            <div className="flex-1">
              {summary ? (
                <MarkdownRenderer content={summary} documentId={documentId} />
              ) : (
                <div className="flex flex-col items-center justify-center h-48 text-slate-400 gap-2">
                  <svg className="w-6 h-6 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <p className="text-xs">Loading case summary...</p>
                </div>
              )}
            </div>
          </div>

          {/* Right Panel: Chat Interface */}
          <div className="w-1/2 bg-white p-6 rounded-2xl shadow-xs border border-slate-200/80 flex flex-col overflow-hidden">
            <div className="flex items-center gap-2.5 border-b border-slate-100 pb-3.5 mb-4">
              <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900 leading-tight">Chat with Document</h2>
                <p className="text-xs text-slate-400">Ask questions with precise page citations</p>
              </div>
            </div>

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
  const [messages, setMessages] = useState<{ role: string; content: string; citations?: any[] }[]>([
    { role: 'ai', content: 'Hello! How can I assist you with this case?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    // Reset chat when documentId changes to maintain isolation between cases
    setMessages([{ role: 'ai', content: 'Hello! How can I assist you with this case?' }]);
    setInput('');
  }, [documentId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/documents/${documentId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMessage }),
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, { role: 'ai', content: data.answer, citations: data.citations }]);
      } else {
        throw new Error('Chat request failed');
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: 'ai', content: 'Sorry, an error occurred while generating the answer. Please try again.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Scrollable Message History */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4 pr-1">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-slate-400 p-6">
            <div className="w-12 h-12 bg-slate-100 text-slate-400 rounded-2xl flex items-center justify-center mb-3">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-sm font-semibold text-slate-600">No messages yet</p>
            <p className="text-xs text-slate-400 mt-1 max-w-xs">Ask specific questions about the case facts, acts, court reasoning, or order details.</p>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={`p-4 rounded-2xl transition-all ${
              m.role === 'user'
                ? 'bg-blue-600 text-white ml-10 shadow-xs'
                : 'bg-slate-50 border border-slate-200/80 mr-6 shadow-2xs'
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  m.role === 'user' ? 'bg-white/20 text-white' : 'bg-blue-600 text-white'
                }`}
              >
                {m.role === 'user' ? 'U' : 'N'}
              </div>
              <span
                className={`text-xs font-semibold ${
                  m.role === 'user' ? 'text-blue-100' : 'text-slate-600'
                }`}
              >
                {m.role === 'user' ? 'You' : 'NyayaAI'}
              </span>
            </div>

            {/* Message Body */}
            {m.role === 'user' ? (
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{m.content}</p>
            ) : (
              <MarkdownRenderer content={m.content} documentId={documentId} />
            )}

            {/* Citations Badges */}
            {m.citations && m.citations.length > 0 && (
              <div className="mt-3.5 pt-3 border-t border-slate-200/60">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                  Page Sources & Citations
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {m.citations.map((c: any, idx: number) => (
                    <a
                      key={idx}
                      href={`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/documents/${documentId}/pages/${c.page}`}
                      target="_blank"
                      rel="noreferrer"
                      className="px-2.5 py-1 bg-blue-100/80 text-blue-700 hover:bg-blue-200 font-semibold text-xs rounded-lg transition-colors cursor-pointer inline-flex items-center gap-1 border border-blue-200/60"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Page {c.page}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="p-4 bg-slate-50 border border-slate-200/80 rounded-2xl mr-10 text-slate-500 text-xs flex items-center gap-2 animate-pulse">
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-ping"></div>
            <span>NyayaAI is retrieving legal evidence and generating response...</span>
          </div>
        )}
        <div ref={chatBottomRef} />
      </div>

      {/* Input Box */}
      <form onSubmit={sendMessage} className="flex items-center gap-2 pt-2 border-t border-slate-100">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask anything about this legal case..."
          className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-5 py-3 bg-blue-600 text-white font-semibold text-sm rounded-xl hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-xs flex items-center gap-1.5"
        >
          <span>Send</span>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
          </svg>
        </button>
      </form>
    </div>
  );
}
