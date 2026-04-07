"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import Link from 'next/link';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const router = useRouter();
  const login = useAuthStore(state => state.login);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // FastAPI OAuth2PasswordRequestForm STRICTLY expects form-data (URL encoded), not JSON!
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });

      // Inject into Zustand global memory
      login(response.data.access_token, response.data.role, response.data.user_id);
      
      // Send user to their specific dashboard
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to authenticate. Check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 flex items-center justify-center p-4">
      <div className="bg-neutral-900 border border-neutral-800 p-10 rounded-3xl shadow-2xl w-full max-w-md relative overflow-hidden">
        {/* Aesthetic Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-2 bg-gradient-to-r from-emerald-400 to-cyan-500 blur-sm opacity-50" />
        
        <h2 className="text-3xl font-extrabold text-white mb-2 tracking-tight">Access Cortex</h2>
        <p className="text-neutral-400 text-sm mb-8">Sign in to manage your AgriFlux network.</p>

        {error && (
          <div className="mb-6 bg-rose-900/30 border border-rose-500/50 text-rose-300 text-sm px-4 py-3 rounded-xl animate-pulse">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">Email Identity</label>
            <input 
              type="email" 
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
              placeholder="farmer@agriflux.com"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">Security Key</label>
            <input 
              type="password" 
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
              placeholder="••••••••"
            />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full relative mt-8 py-3.5 rounded-xl font-bold tracking-wide text-white overflow-hidden group outline-none"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-600 to-cyan-600 opacity-90 group-hover:opacity-100 transition-opacity" />
            <span className="relative flex items-center justify-center">
              {loading ? "AUTHENTICATING..." : "INITIATE SESSION"}
            </span>
          </button>
        </form>

        <p className="mt-8 text-center text-sm text-neutral-500">
          Unregistered node? <Link href="/auth/signup" className="text-cyan-400 hover:text-cyan-300 transition-colors">Request Access</Link>
        </p>
      </div>
    </div>
  );
}
