"use client";

import React, { useState, useEffect } from 'react';

type Status = 'uploading' | 'processing_scanned_pages' | 'extracting_case_information' | 'creating_searchable_index' | 'generating_summary' | 'ready' | 'failed' | 'not_found';

export default function CaseDashboard({ documentId }: { documentId: string }) {
  const [status, setStatus] = useState<Status>('uploading');
  const [progress, setProgress] = useState(0);
  const [summary, setSummary] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'summary' | 'chat'>('summary');

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
    return <div className="p-8 text-red-500 text-center">Error processing document.</div>;
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
    <div className="flex flex-col h-screen overflow-hidden">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">NyayaAI - Case Workspace</h1>
        <div className="flex gap-4">
          <button 
            className={`px-4 py-2 text-sm font-medium rounded-md ${activeTab === 'summary' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}
            onClick={() => setActiveTab('summary')}
          >
            Summary
          </button>
          <button 
            className={`px-4 py-2 text-sm font-medium rounded-md ${activeTab === 'chat' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}`}
            onClick={() => setActiveTab('chat')}
          >
            Chat
          </button>
        </div>
      </header>
      
      <div className="flex-1 overflow-auto bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto bg-white p-8 rounded-lg shadow-sm border">
          {activeTab === 'summary' ? (
             <div>
               <h2 className="text-2xl font-bold border-b pb-4 mb-4">Case Summary</h2>
               {summary ? (
                 <div className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">
                   {typeof summary === 'string' ? summary : JSON.stringify(summary, null, 2)}
                 </div>
               ) : (
                 <p>Loading summary...</p>
               )}
             </div>
          ) : (
             <ChatInterface documentId={documentId} />
          )}
        </div>
      </div>
    </div>
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
    <div className="flex flex-col h-[70vh]">
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
