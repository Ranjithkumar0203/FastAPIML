export interface LoginResponse { access_token: string; token_type: string; }
export interface User { id: string; email: string; }
export interface Thread { id: string; title: string; created_at: string; updated_at: string; }
export interface ChatMessage { id?: string; role: 'user' | 'assistant'; content: string; created_at?: string; }
