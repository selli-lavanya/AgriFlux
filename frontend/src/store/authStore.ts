import { create } from 'zustand';

interface AuthState {
  token: string | null;
  role: string | null;
  userId: number | null;
  login: (token: string, role: string, userId: number) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: typeof window !== 'undefined' ? localStorage.getItem('agriflux_token') : null,
  role: typeof window !== 'undefined' ? localStorage.getItem('agriflux_role') : null,
  userId: typeof window !== 'undefined' ? Number(localStorage.getItem('agriflux_user_id')) : null,
  
  login: (token: string, role: string, userId: number) => {
    localStorage.setItem('agriflux_token', token);
    localStorage.setItem('agriflux_role', role);
    localStorage.setItem('agriflux_user_id', userId.toString());
    set({ token, role, userId });
  },
  
  logout: () => {
    localStorage.removeItem('agriflux_token');
    localStorage.removeItem('agriflux_role');
    localStorage.removeItem('agriflux_user_id');
    set({ token: null, role: null, userId: null });
  },
}));
