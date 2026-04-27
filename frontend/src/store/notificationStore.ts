import { create } from 'zustand';

export interface AppNotification {
  id: string; // Unique ID per message, using timestamp for simplicity
  event_type: string;
  entity_type: string;
  entity_id: number;
  message: string;
  timestamp: string;
  read: boolean;
}

interface NotificationStore {
  notifications: AppNotification[];
  addNotification: (notification: AppNotification) => void;
  markAsRead: (id: string) => void;
  clearAll: () => void;
}

export const useNotificationStore = create<NotificationStore>((set) => ({
  notifications: [],
  addNotification: (notification) => set((state) => {
    // Prevent duplicates by ID
    if (state.notifications.some(n => n.id === notification.id)) return state;
    return { notifications: [notification, ...state.notifications] };
  }),
  markAsRead: (id) => set((state) => ({
    notifications: state.notifications.map((n) => n.id === id ? { ...n, read: true } : n)
  })),
  clearAll: () => set({ notifications: [] })
}));
