import { create } from 'zustand';

interface AdminState {
  token: string;
  setToken: (token: string) => void;
}

const initialToken = typeof window !== 'undefined' ? localStorage.getItem('lunia_admin_token') ?? '' : '';

export const useAdminStore = create<AdminState>((set) => ({
  token: initialToken,
  setToken: (token: string) => {
    set({ token });
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('lunia_admin_token', token);
      } else {
        localStorage.removeItem('lunia_admin_token');
      }
    }
  },
}));

export function adminHeaders(token: string) {
  return token ? { 'X-Admin-Token': token } : undefined;
}
