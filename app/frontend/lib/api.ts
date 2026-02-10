export interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
}

export interface ChatResponse {
    message: string;
    next_action?: string;
    retrieved_projects: string[];
    mode: 'concierge' | 'lead_capture';
}

export interface Lead {
    name: string;
    phone: string;
    email?: string;
    interest_projects: string[];
    unit_type?: string;
    budget?: string;
    intent?: string;
    timeline?: string;
    region?: string;
    next_step?: string;
    session_id: string;
}

const API_BASE = ''; // Relative path handled by Next.js rewrites

export const api = {
    chat: async (sessionId: string, messages: ChatMessage[]): Promise<ChatResponse> => {
        const res = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, messages, locale: 'en' }),
        });
        if (!res.ok) throw new Error('Chat request failed');
        return res.json();
    },

    createLead: async (lead: Lead) => {
        const res = await fetch(`${API_BASE}/api/lead`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(lead),
        });
        if (!res.ok) throw new Error('Lead creation failed');
        return res.json();
    },

    getLeads: async (password: string) => {
        // Next.js rewrite maps /admin-api -> Backend /admin
        const res = await fetch(`${API_BASE}/admin-api/leads`, {
            headers: { 'password': password }
        });
        if (!res.ok) throw new Error('Failed to fetch leads');
        return res.json();
    }
};
