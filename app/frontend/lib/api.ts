export interface ChatMessage {
    role: "user" | "assistant";
    content: string;
    cta?: {
      label: string;
      action: "link" | "callback";
      url?: string;
    };
    cta_card?: {
      title: string;
      price?: string;
      location?: string;
      image?: string;
      cta?: string;
      actions?: Array<{
        label: string;
        type: "link" | "callback";
        url?: string;
      }>;
    };
  }
export interface CTACard {
    title: string;
    price?: string;
    location?: string;
    image?: string;
    cta?: string;
    link?: string;
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

// Use relative paths so Next.js proxy/rewrites apply consistently.
// (Chat UI uses `/api/health` already; keep chat endpoints aligned.)
const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";

// If `NEXT_PUBLIC_BACKEND_URL` is set, we connect directly to the backend.
// Otherwise we fall back to relative paths (works in dev when Next rewrites are enabled).
const withBackend = (path: string) => {
    return backendUrl ? `${backendUrl}${path}` : path;
};

export const api = {
    chat: async (sessionId: string, messages: ChatMessage[]): Promise<ChatResponse> => {
        const res = await fetch(withBackend("/api/chat"), {
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
        onDone: (data: { 
            retrieved_projects: string[]; 
            mode: 'concierge' | 'lead_capture';
            cta?: ChatMessage["cta"]; // ✅ ADD THIS
            cta_card?: ChatMessage["cta_card"];
          }) => void
    ) => {
        const res = await fetch(withBackend("/api/chat/stream"), {
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
                const seg = line.trim();
                if (seg.startsWith('data:')) {
                    try {
                        // Accept both `data: <json>` and `data:<json>` formats.
                        const jsonPart = seg.replace(/^data:\s*/, '');
                        const data = JSON.parse(jsonPart);
                        if (data.done) {
                            onDone({
                                retrieved_projects: data.retrieved_projects || [],
                                mode: data.mode || 'concierge',
                                cta: data.cta,
                                cta_card: data.cta_card
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
        const res = await fetch(withBackend("/api/lead"), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(lead),
        });
        if (!res.ok) throw new Error('Lead creation failed');
        return res.json();
    },

    getLeads: async (password: string) => {
        // Legacy endpoint shape (kept for compatibility).
        const res = await fetch(backendUrl ? `${backendUrl}/api/admin/leads` : "/admin-api/leads", {
            headers: { 'password': password }
        });
        if (!res.ok) throw new Error('Failed to fetch leads');
        return res.json();
    }
};
