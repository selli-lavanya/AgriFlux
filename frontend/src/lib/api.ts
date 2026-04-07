import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to natively pull the JWT Access Token from local browser storage and inject it
api.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('agriflux_token') : null;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
