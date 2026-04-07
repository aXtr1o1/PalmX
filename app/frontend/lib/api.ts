export interface BudgetSelector {
    label: string;
    value: number;
    step: number;
    min: number;
    max: number;
}
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
    project_cards?: ProjectCard[];
    trim_intro?: boolean;
    suggested_actions?: string[];
     budget_selector?: BudgetSelector | null;  // LLM-generated next-step button labels
  }

export interface ProjectCard {
    id: string;
    title: string;
    price?: string;
    location?: string;
    type?: string;
    status?: string;
    amenities?: string[];
    url?: string;
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

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";

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
            mode: 'concierge' | 'lead_capture' | 'support' | string;
            cta?: ChatMessage["cta"];
            cta_card?: ChatMessage["cta_card"];
            project_cards?: ProjectCard[];
            trim_intro?: boolean;
            persona_stage?: string;
            suggested_actions?: string[];
            budget_selector?: BudgetSelector | null;
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
                        const jsonPart = seg.replace(/^data:\s*/, '');
                        const parsed = JSON.parse(jsonPart);
                        if (parsed.done) {
                            onDone({
                                retrieved_projects: parsed.retrieved_projects || [],
                                mode: parsed.mode || 'concierge',
                                cta: parsed.cta,
                                cta_card: parsed.cta_card,
                                project_cards: parsed.project_cards,
                                trim_intro: parsed.trim_intro,
                                persona_stage: parsed.persona_stage,
                                suggested_actions: parsed.suggested_actions || [],
                                budget_selector: parsed.budget_selector || null,
                            });
                        } else if (parsed.token) {
                            onToken(parsed.token);
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
        const res = await fetch(backendUrl ? `${backendUrl}/api/admin/leads` : "/admin-api/leads", {
            headers: { 'password': password }
        });
        if (!res.ok) throw new Error('Failed to fetch leads');
        return res.json();
    }
};