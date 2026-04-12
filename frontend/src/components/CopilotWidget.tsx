"use client";

import { useState, useRef, useEffect } from 'react';
import api from '@/lib/api';
import { create } from 'zustand';
import { useAuthStore } from '@/store/authStore';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface CopilotStore {
  history: ChatMessage[];
  addMessage: (msg: ChatMessage) => void;
  clearHistory: () => void;
}

const useCopilotStore = create<CopilotStore>((set) => ({
  history: [],
  addMessage: (msg) => set((state) => ({ history: [...state.history, msg] })),
  clearHistory: () => set({ history: [] })
}));

export default function CopilotWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { history, addMessage, clearHistory } = useCopilotStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  const { userId } = useAuthStore();

  // Fix state leakage: clear chat history when auth context changes
  useEffect(() => {
    clearHistory();
  }, [userId, clearHistory]);

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [history, isOpen]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    addMessage({ role: 'user', content: userMessage });
    setIsLoading(true);

    try {
      const response = await api.post('/copilot/query', {
        message: userMessage,
        history: history
      });
      addMessage({ role: 'assistant', content: response.data.reply });
    } catch (err: any) {
      console.error(err);
      const detail = err.response?.data?.detail || "Could not reach AI Core.";
      addMessage({ role: 'assistant', content: `SYSTEM ERROR: ${detail}` });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-indigo-600 rounded-full flex items-center justify-center shadow-[0_0_20px_rgba(79,70,229,0.5)] hover:bg-indigo-500 transition-colors z-[1000]"
      >
        <span className="text-2xl">🤖</span>
      </button>

      {isOpen && (
        <div className="fixed bottom-24 right-6 w-80 md:w-96 bg-neutral-900 border border-indigo-500/30 rounded-2xl shadow-2xl flex flex-col z-[1000] overflow-hidden">
          <div className="bg-indigo-900/50 p-4 border-b border-indigo-500/30 flex justify-between items-center">
            <div>
               <h3 className="text-indigo-400 font-bold tracking-widest text-sm flex items-center gap-2">
                 <span className="relative flex h-2 w-2"><span className="animate-ping absolute h-full w-full rounded-full bg-indigo-400 opacity-75"></span><span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span></span>
                 AgriFlux Copilot
               </h3>
               <p className="text-[10px] text-indigo-300/50 uppercase mt-1">Live Database Linked</p>
            </div>
            <button onClick={clearHistory} className="text-xs text-neutral-500 hover:text-white transition">Clear</button>
          </div>
          
          <div className="flex-1 h-80 overflow-y-auto p-4 space-y-4">
            {history.length === 0 && (
               <div className="text-center text-neutral-500 text-xs italic mt-10 p-4">
                 Awaiting query. Try asking:<br/> "Which farms need harvesters?"<br/>"What is the network availability?"
               </div>
            )}
            {history.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] p-3 rounded-2xl text-sm ${msg.role === 'user' ? 'bg-indigo-600/20 text-indigo-100 border border-indigo-500/30' : 'bg-neutral-800 text-neutral-300 border border-neutral-700'} whitespace-pre-wrap`}>
                  {msg.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-neutral-800 text-neutral-400 p-3 rounded-2xl border border-neutral-700 text-xs flex items-center gap-2">
                  <span className="animate-pulse">●</span><span className="animate-pulse delay-75">●</span><span className="animate-pulse delay-150">●</span> Gathering live parameters...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSend} className="p-3 border-t border-neutral-800 bg-black/50">
            <div className="relative">
              <input 
                type="text" 
                placeholder="Query Operational Matrix..." 
                className="w-full bg-neutral-800 border border-neutral-700 rounded-xl p-3 pr-12 text-sm focus:outline-none focus:border-indigo-500 text-white placeholder-neutral-500"
                value={input}
                onChange={e => setInput(e.target.value)}
                disabled={isLoading}
              />
              <button 
                type="submit" 
                disabled={isLoading || !input.trim()}
                className="absolute right-2 top-2 bg-indigo-600/30 text-indigo-400 p-1.5 rounded-lg hover:bg-indigo-600 hover:text-white transition cursor-pointer disabled:opacity-50"
              >
                {'➤'}
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
