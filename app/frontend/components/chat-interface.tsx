"use client";

import { useEffect, useState, useRef } from "react";
import { Send, MapPin, Building2, User, Sparkles, ArrowRight } from "lucide-react";
import { api, ChatMessage, Lead } from "@/lib/api";
import { cn } from "@/lib/utils";

const SESSION_ID_KEY = "palmx_sess_id";

const QUICK_PROMPTS = [
    "Villa in Badya starting 10M",
    "Apartments in New Cairo",
    "Payment plans for The Crown",
    "Ready to move options"
];

export default function ChatInterface() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [sessionId, setSessionId] = useState("");
    const [mode, setMode] = useState<'concierge' | 'lead_capture'>('concierge');
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        let sid = localStorage.getItem(SESSION_ID_KEY);
        if (!sid) {
            sid = Math.random().toString(36).substring(7);
            localStorage.setItem(SESSION_ID_KEY, sid);
        }
        setSessionId(sid);
    }, []);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, loading]);

    const handleSubmit = async (e?: React.FormEvent, quickPrompt?: string) => {
        e?.preventDefault();
        const text = quickPrompt || input;
        if (!text.trim() || loading) return;

        const userMsg = { role: "user" as const, content: text };
        setMessages(prev => [...prev, userMsg]);
        setInput("");
        setLoading(true);

        try {
            const history = [...messages, userMsg];
            const response = await api.chat(sessionId, history);

            setMessages(prev => [...prev, { role: "assistant", content: response.message }]);

            if (response.mode === 'lead_capture' && mode !== 'lead_capture') {
                setMode('lead_capture');
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
        <div className="flex flex-col h-[85vh] w-full max-w-5xl mx-auto bg-white shadow-2xl rounded-2xl overflow-hidden border border-gray-100 flex-1 relative">

            {/* Elegant Header */}
            <div className="bg-secondary text-white p-6 flex items-center justify-between shadow-md z-10">
                <div className="flex items-center gap-4">
                    <div className="relative">
                        <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center text-white font-serif font-bold text-lg ring-4 ring-white/10 stamp-effect shadow-lg">
                            PH
                        </div>
                        <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-secondary"></div>
                    </div>
                    <div>
                        <h1 className="font-serif text-xl tracking-wider font-medium">PALM HILLS</h1>
                        <div className="flex items-center gap-2 opacity-80 text-xs tracking-widest uppercase">
                            <Sparkles size={10} className="text-primary" />
                            <span>Concierge AI</span>
                        </div>
                    </div>
                </div>
                <div className="hidden md:block text-right">
                    <div className="text-xs text-gray-400 font-mono mb-1">PILOT BUILD v1.0</div>
                    <div className="text-[10px] uppercase tracking-widest px-2 py-1 bg-white/5 rounded-full inline-block">
                        {mode === 'concierge' ? 'Exploration Mode' : 'Concierge Assistance'}
                    </div>
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 bg-gray-50/50 relative overflow-hidden flex flex-col">

                {/* Background Decor */}
                <div className="absolute top-0 left-0 w-full h-[300px] bg-gradient-to-b from-gray-100 to-transparent pointer-events-none opacity-50" />

                <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-8 z-10 scroll-smooth">

                    {/* Welcome State */}
                    {messages.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-full space-y-8 opacity-0 animate-in fade-in slide-in-from-bottom-4 duration-700 fill-mode-forwards" style={{ animationFillMode: 'forwards' }}>
                            <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center shadow-lg mb-4">
                                <Building2 size={32} className="text-secondary opacity-20" />
                            </div>
                            <div className="text-center max-w-md space-y-3">
                                <h2 className="font-serif text-3xl text-secondary">Welcome Home</h2>
                                <p className="text-gray-500 font-light leading-relaxed">
                                    I am your personal guide to Palm Hills. Explore our premier communities,
                                    check availability, and find your perfect home.
                                </p>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-lg">
                                {QUICK_PROMPTS.map((p, i) => (
                                    <button
                                        key={i}
                                        onClick={() => handleSubmit(undefined, p)}
                                        className="p-4 bg-white hover:bg-gray-50 border border-gray-200 hover:border-primary/30 rounded-xl text-left text-sm text-gray-600 transition-all shadow-sm hover:shadow-md group flex items-center justify-between"
                                    >
                                        <span>{p}</span>
                                        <ArrowRight size={14} className="opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all text-primary" />
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Messages */}
                    {messages.map((m, i) => (
                        <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} group`}>

                            {m.role === 'assistant' && (
                                <div className="w-8 h-8 rounded-full bg-secondary flex-shrink-0 flex items-center justify-center text-white text-xs font-serif mr-3 mt-1 shadow-md">
                                    PH
                                </div>
                            )}

                            <div className={cn(
                                "max-w-[85%] md:max-w-[75%] p-5 text-sm md:text-base leading-relaxed shadow-sm transition-all relative group-hover:shadow-md",
                                m.role === 'user'
                                    ? "bg-secondary text-white rounded-2xl rounded-tr-sm"
                                    : "bg-white text-gray-800 border border-gray-100 rounded-2xl rounded-tl-sm ring-1 ring-gray-100/50"
                            )}>
                                <div className="whitespace-pre-wrap font-light">{m.content}</div>
                                {m.role === 'assistant' && (
                                    <div className="absolute -bottom-5 left-0 opacity-0 group-hover:opacity-100 transition-opacity flex items-center space-x-2 text-[10px] text-gray-400 uppercase tracking-widest mt-1">
                                        <span className="w-1 h-1 rounded-full bg-primary"></span>
                                        <span>Verified Knowledge Base</span>
                                    </div>
                                )}
                            </div>

                            {m.role === 'user' && (
                                <div className="w-8 h-8 rounded-full bg-gray-200 flex-shrink-0 flex items-center justify-center text-gray-500 ml-3 mt-1">
                                    <User size={14} />
                                </div>
                            )}
                        </div>
                    ))}

                    {/* Loading Indicator */}
                    {loading && (
                        <div className="flex justify-start">
                            <div className="w-8 h-8 rounded-full bg-secondary flex-shrink-0 flex items-center justify-center text-white text-xs font-serif mr-3 mt-1 shadow-md">PH</div>
                            <div className="bg-white p-5 rounded-2xl rounded-tl-sm shadow-sm border border-gray-100 flex items-center space-x-2">
                                <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Input Area */}
            <div className="bg-white p-4 md:p-6 border-t border-gray-100 z-20">
                <form onSubmit={(e) => handleSubmit(e)} className="relative max-w-4xl mx-auto">
                    <div className="relative group">
                        <input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder={loading ? "Thinking..." : "Ask me anything about Palm Hills..."}
                            className={cn(
                                "w-full pl-6 pr-14 py-5 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-2 focus:ring-primary/10 focus:border-primary/30 transition-all font-light text-gray-700 shadow-inner",
                                loading && "opacity-50 cursor-not-allowed"
                            )}
                            disabled={loading}
                        />
                        <button
                            type="submit"
                            disabled={loading || !input.trim()}
                            className="absolute right-3 top-3 p-2 bg-primary text-white rounded-xl shadow-lg hover:bg-primary/90 hover:scale-105 disabled:opacity-50 disabled:hover:scale-100 transition-all duration-300"
                        >
                            <Send size={18} />
                        </button>
                    </div>
                    <div className="mt-3 flex justify-center items-center space-x-4 text-[10px] text-gray-400 uppercase tracking-widest font-medium">
                        <span className="flex items-center gap-1"><MapPin size={10} /> 14 verified compounds</span>
                        <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
                        <span className="flex items-center gap-1"><Building2 size={10} /> Real-time pricing</span>
                    </div>
                </form>
            </div>

        </div>
    );
}
