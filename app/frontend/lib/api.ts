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

    chatStream: async (
        sessionId: string,
        messages: ChatMessage[],
        onToken: (token: string) => void,
        onDone: (data: { retrieved_projects: string[]; mode: 'concierge' | 'lead_capture' }) => void
    ) => {
        const res = await fetch(`${API_BASE}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, messages, locale: 'en' }),
        });
        if (!res.ok) throw new Error('Stream request failed');

        const reader = res.body?.getReader();
        if (!reader) throw new Error('No reader available');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.done) {
                            onDone({
                                retrieved_projects: data.retrieved_projects || [],
                                mode: data.mode || 'concierge'
                            });
                        } else if (data.token) {
                            onToken(data.token);
                        }
                    } catch (e) {
                        // Skip malformed lines
                    }
                }
            }
        }
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
