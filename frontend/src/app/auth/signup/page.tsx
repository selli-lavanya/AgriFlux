"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import Link from 'next/link';

export default function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('farmer');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Signup expects raw JSON!
      await api.post('/auth/signup', { email, password, role });
      // Redirect to login to fetch their token
      router.push('/auth/login');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to register. Email might be in use.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 flex items-center justify-center p-4">
      <div className="bg-neutral-900 border border-neutral-800 p-10 rounded-3xl shadow-2xl w-full max-w-md relative overflow-hidden">
        {/* Aesthetic Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-2 bg-gradient-to-r from-cyan-400 to-indigo-500 blur-sm opacity-50" />
        
        <h2 className="text-3xl font-extrabold text-white mb-2 tracking-tight">Node Registration</h2>
        <p className="text-neutral-400 text-sm mb-8">Join the AgriFlux logistics network.</p>

        {error && (
          <div className="mb-6 bg-rose-900/30 border border-rose-500/50 text-rose-300 text-sm px-4 py-3 rounded-xl">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">Network Profile</label>
            <select 
              value={role} 
              onChange={e => setRole(e.target.value)} 
              className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500 appearance-none transition-all"
            >
              <option value="farmer">Agricultural Producer (Farmer)</option>
              <option value="machine_owner">Machinery Outfitter</option>
              <option value="labour_team">Labour Syndicate Leader</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">Email Identity</label>
            <input 
              type="email" 
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500 transition-all"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">Security Key</label>
            <input 
              type="password" 
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500 transition-all"
            />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full relative mt-8 py-3.5 rounded-xl font-bold tracking-wide text-white overflow-hidden group outline-none"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-600 to-indigo-600 opacity-90 group-hover:opacity-100 transition-opacity" />
            <span className="relative flex items-center justify-center">
              {loading ? "INITIALIZING..." : "CREATE NODE"}
            </span>
          </button>
        </form>

        <p className="mt-8 text-center text-sm text-neutral-500">
          Already verified? <Link href="/auth/login" className="text-indigo-400 hover:text-indigo-300 transition-colors">Establish Connection</Link>
        </p>
      </div>
    </div>
  );
}
