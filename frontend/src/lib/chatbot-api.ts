// Type definitions for chat and message
export type Chat = {
  id: string;
  title: string;
  messages: Message[];
  created_at: string;
  last_updated: string;
};

export type Message = {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';
const CHAT_REQUEST_TIMEOUT_MS = Number(import.meta.env.VITE_CHAT_REQUEST_TIMEOUT_MS || 90000);

export const chatbotApi = {
  async getAllChats() {
    const res = await fetch(`${API_BASE_URL}/chats`);
    return await res.json();
  },
  async getUpcomingFestivals() {
    const res = await fetch(`${API_BASE_URL}/festivals/upcoming`);
    const result = await res.json();
    // Ensure compatibility with frontend expectations
    if (result.success && result.upcoming_festivals) {
      return { success: true, data: result.upcoming_festivals };
    }
    return result;
  },
  async createNewChat() {
    const res = await fetch(`${API_BASE_URL}/chat/new`, { method: 'POST' });
    const result = await res.json();
    // Ensure compatibility with frontend expectations
    if (result.success && result.chat) {
      return { success: true, data: result.chat };
    }
    return result;
  },
  async sendMessage(chatId: string, message: string, language: string = 'en') {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), CHAT_REQUEST_TIMEOUT_MS);
      try {
        const res = await fetch(`${API_BASE_URL}/chat/${chatId}/message`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, language }),
          signal: controller.signal,
        });
        const result = await res.json();
        // Ensure compatibility with frontend expectations
        if (result.success && result.chat) {
          return { success: true, data: { chat: result.chat } };
        }
        return result;
      } catch (error: unknown) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          return {
            success: false,
            error: 'Request timed out. Please try a shorter question or retry in a moment.',
            timeout: true,
          };
        }
        throw error;
      } finally {
        clearTimeout(timeoutId);
      }
  },
  async deleteChat(chatId: string) {
    const res = await fetch(`${API_BASE_URL}/chat/${chatId}`, { method: 'DELETE' });
    return await res.json();
  },
  async sendMail() {
    const res = await fetch(`${API_BASE_URL}/send-mail`, { method: 'POST' });
    return await res.json();
  },
};

export async function checkBackendConnection(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    if (!res.ok) return false;
    const data = await res.json();
    return data.status === 'healthy';
  } catch {
    return false;
  }
}
