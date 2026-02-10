"use client";

import { useEffect, useState, useRef } from "react";
import { Send, MapPin, Building2, User } from "lucide-react";
import { api, ChatMessage, Lead } from "@/lib/api";
import { cn } from "@/lib/utils";

const SESSION_ID_KEY = "palmx_sess_id";

export default function ChatInterface() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [sessionId, setSessionId] = useState("");
    const [mode, setMode] = useState<'concierge' | 'lead_capture'>('concierge');

    // Lead Capture State
    const [leadFormOpen, setLeadFormOpen] = useState(false);
    const [leadData, setLeadData] = useState<Partial<Lead>>({});

    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        let sid = localStorage.getItem(SESSION_ID_KEY);
        if (!sid) {
            sid = Math.random().toString(36).substring(7);
            localStorage.setItem(SESSION_ID_KEY, sid);
        }
        setSessionId(sid);

        // Initial greeting if empty
        if (messages.length === 0) {
            setMessages([
                { role: "assistant", content: "Welcome to Palm Hills. I am PalmX, your property concierge. How may I assist you today?" }
            ]);
        }
    }, []);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSubmit = async (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = { role: "user" as const, content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput("");
        setLoading(true);

        try {
            const history = [...messages, userMsg];
            const response = await api.chat(sessionId, history);

            setMessages(prev => [...prev, { role: "assistant", content: response.message }]);

            if (response.mode === 'lead_capture' && mode !== 'lead_capture') {
                setMode('lead_capture');
                // Trigger lead form if strictly needed or just continue chat flow
                // For pilot, we might continue chat flow until finalized
            } else {
                setMode(response.mode);
            }

        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, { role: "assistant", content: "I'm having trouble connecting. Please try again." }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-[600px] w-full max-w-4xl mx-auto bg-white shadow-xl rounded-xl overflow-hidden border border-gray-100">

            {/* Header */}
            <div className="bg-secondary p-4 flex items-center justify-between text-white">
                <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center font-serif text-xs font-bold ring-2 ring-white/20 stamp-effect">
                        PH
                    </div>
                    <div>
                        <h1 className="font-serif font-semibold tracking-wide text-sm">PALM HILLS</h1>
                        <p className="text-[10px] text-gray-300 tracking-wider">PROPERTY CONCIERGE</p>
                    </div>
                </div>
                <div className="text-xs text-gray-400 font-mono">PILOT v1.0</div>
            </div>

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50/50">
                {messages.map((m, i) => (
                    <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={cn(
                            "max-w-[80%] p-4 text-sm leading-relaxed shadow-sm",
                            m.role === 'user'
                                ? "bg-secondary text-white rounded-2xl rounded-tr-none"
                                : "bg-white text-gray-800 border border-gray-100 rounded-2xl rounded-tl-none"
                        )}>
                            <div className="whitespace-pre-wrap">{m.content}</div>
                            {m.role === 'assistant' && (
                                <div className="mt-2 flex items-center space-x-2 text-[10px] text-gray-400 uppercase tracking-widest">
                                    <span className="w-1 h-1 rounded-full bg-primary"></span>
                                    <span>PalmX verified</span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-white p-4 rounded-2xl rounded-tl-none shadow-sm border border-gray-100 flex items-center space-x-2">
                            <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                            <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                            <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                    </div>
                )}
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="p-4 bg-white border-t border-gray-100">
                <div className="relative">
                    <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask about projects, pricing, or unit availability..."
                        className="w-full pl-4 pr-12 py-4 bg-gray-50 border-0 rounded-xl focus:ring-1 focus:ring-primary/20 text-sm placeholder:text-gray-400 font-light shadow-inner"
                        disabled={loading}
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className="absolute right-2 top-2 p-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
                    >
                        <Send size={18} />
                    </button>
                </div>
                <div className="mt-2 flex justify-center text-[10px] text-gray-400">
                    Powered by verified Palm Hills KB • No database connection
                </div>
            </form>

        </div>
    );
}
