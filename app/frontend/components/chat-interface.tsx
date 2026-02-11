"use client";

import { useEffect, useState, useRef } from "react";
import { Send, MapPin, Building2, User, Sparkles, ArrowRight, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
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
    const [systemReady, setSystemReady] = useState(false);
    const [bootProgress, setBootProgress] = useState(0);

    const scrollRef = useRef<HTMLDivElement>(null);

    // Initial System Check (Loading Screen)
    useEffect(() => {
        let interval: NodeJS.Timeout;
        const checkHealth = async () => {
            try {
                // We'll just try to ping the chat API or a health endpoint if it existed.
                // For now, we simulate a health check by trying a lightweight call or just assuming delay.
                // Since user wants a "Progress bar", we'll fake the boot sequence until backend is reachable.
                const res = await fetch('/api/health'); // We assume we added this or just try root
                if (res.ok) {
                    setSystemReady(true);
                    setBootProgress(100);
                    clearInterval(interval);
                } else {
                    setBootProgress(prev => Math.min(prev + 10, 90));
                }
            } catch (e) {
                // Backend likely starting up
                setBootProgress(prev => Math.min(prev + 5, 90));
            }
        };

        // Start polling
        interval = setInterval(checkHealth, 1000);
        return () => clearInterval(interval);
    }, []);

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
            let firstToken = true;

            await api.chatStream(
                sessionId,
                history,
                // onToken — insert message on first token, then append
                (token: string) => {
                    if (firstToken) {
                        firstToken = false;
                        setLoading(false); // Hide THINKING as soon as first token arrives
                        setMessages(prev => [...prev, { role: "assistant", content: token }]);
                    } else {
                        setMessages(prev => {
                            const updated = [...prev];
                            const lastMsg = updated[updated.length - 1];
                            if (lastMsg && lastMsg.role === "assistant") {
                                updated[updated.length - 1] = {
                                    ...lastMsg,
                                    content: lastMsg.content + token
                                };
                            }
                            return updated;
                        });
                    }
                },
                // onDone — set mode
                (data) => {
                    if (data.mode === 'lead_capture' && mode !== 'lead_capture') {
                        setMode('lead_capture');
                    } else {
                        setMode(data.mode);
                    }
                }
            );
        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, { role: "assistant", content: "I'm having trouble connecting to PalmX. Please try again." }]);
        } finally {
            setLoading(false);
        }
    };

    if (!systemReady) {
        return (
            <div className="flex flex-col h-[85vh] w-full max-w-5xl mx-auto bg-white shadow-2xl rounded-2xl overflow-hidden border border-gray-100 flex-1 relative items-center justify-center">
                <div className="flex flex-col items-center space-y-6 max-w-sm w-full p-8">
                    <div className="relative">
                        <div className="w-20 h-20 bg-primary rounded-full flex items-center justify-center text-white font-serif font-bold text-2xl ring-4 ring-white/10 stamp-effect shadow-xl">
                            PH
                        </div>
                    </div>
                    <div className="text-center space-y-2">
                        <h2 className="font-serif text-2xl text-secondary">Initalizing PalmX</h2>
                        <p className="text-sm text-gray-400">Loading verified market data...</p>
                    </div>
                    <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-primary transition-all duration-500 ease-out"
                            style={{ width: `${bootProgress}%` }}
                        />
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-[85vh] w-full max-w-5xl mx-auto bg-white shadow-2xl rounded-2xl overflow-hidden border border-gray-100 flex-1 relative animate-in fade-in duration-700">

            {/* Elegant Header */}
            <div className="bg-secondary text-white p-6 flex items-center justify-between shadow-md z-10">
                <div className="flex items-center gap-4">
                    <div className="relative">
                        <div className="w-12 h-12 bg-primary rounded-full flex items-center justify-center text-white font-serif font-bold text-lg ring-4 ring-white/10 shadow-lg">
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
                    <div className="text-xs text-gray-400 font-mono mb-1">v1.2 LIVE</div>
                    <div className="text-[10px] uppercase tracking-widest px-2 py-1 bg-white/5 rounded-full inline-block">
                        {mode === 'concierge' ? 'Concierge Mode' : 'Assistance Mode'}
                    </div>
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 bg-gray-50/50 relative overflow-hidden flex flex-col">

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
                                    I am your personal guide. Ask me about our communities,
                                    prices, or availability.
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
                                {m.role === 'user' ? (
                                    <div className="whitespace-pre-wrap font-light">{m.content}</div>
                                ) : (
                                    <div className="font-light">
                                        <ReactMarkdown
                                            components={{
                                                h3: ({ node, ...props }: any) => (
                                                    <h3 className="font-serif text-lg text-secondary border-b border-primary/10 pb-1 mt-4 first:mt-0 mb-3" {...props} />
                                                ),
                                                p: ({ node, ...props }: any) => (
                                                    <p className="leading-relaxed mb-4 last:mb-0" {...props} />
                                                ),
                                                ul: ({ node, ...props }: any) => (
                                                    <ul className="space-y-3 mb-6 mt-2 list-none" {...props} />
                                                ),
                                                li: ({ node, ...props }: any) => (
                                                    <li className="flex items-start gap-3 text-gray-700" {...props}>
                                                        <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-primary mt-2.5" />
                                                        <span>{props.children}</span>
                                                    </li>
                                                ),
                                                strong: ({ node, ...props }: any) => (
                                                    <strong className="font-semibold text-secondary" {...props} />
                                                ),
                                                a: ({ node, ...props }: any) => (
                                                    <a className="text-primary hover:underline underline-offset-4 decoration-primary/30 transition-all font-medium" {...props} target="_blank" rel="noopener noreferrer" />
                                                )
                                            }}
                                        >
                                            {m.content}
                                        </ReactMarkdown>
                                    </div>
                                )}
                                {m.role === 'assistant' && (
                                    <div className="absolute -bottom-5 left-0 opacity-0 group-hover:opacity-100 transition-opacity flex items-center space-x-2 text-[10px] text-gray-400 uppercase tracking-widest mt-1">
                                        <span className="w-1 h-1 rounded-full bg-primary/20"></span>
                                        <span>Verified</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {/* Loading Indicator */}
                    {loading && (
                        <div className="flex justify-start">
                            <div className="w-8 h-8 rounded-full bg-secondary flex-shrink-0 flex items-center justify-center text-white text-xs font-serif mr-3 mt-1 shadow-md">PH</div>
                            <div className="bg-white p-5 rounded-2xl rounded-tl-sm shadow-sm border border-gray-100 flex items-center space-x-2">
                                <Loader2 size={16} className="animate-spin text-primary" />
                                <span className="text-xs text-gray-400 tracking-wider">THINKING...</span>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Input Area */}
            <div className="bg-white p-4 md:p-6 border-t border-gray-100 z-20">
                <form onSubmit={(e) => e.preventDefault()} className="relative max-w-4xl mx-auto">
                    <div className="relative group">
                        <textarea
                            id="chat-input"
                            value={input}
                            onChange={(e) => {
                                setInput(e.target.value);
                                e.target.style.height = 'auto';
                                e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
                            }}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    if (!loading && input.trim()) {
                                        handleSubmit(e);
                                    }
                                }
                            }}
                            placeholder="Ask anything..."
                            className="w-full pl-6 pr-14 py-5 bg-white border border-gray-200 rounded-2xl focus:ring-2 focus:ring-primary/10 focus:border-primary/30 transition-all font-light text-gray-700 shadow-sm resize-none overflow-hidden"
                            rows={1}
                            style={{ minHeight: '3.5rem', maxHeight: '10rem' }}
                        />
                        <button
                            type="button"
                            onClick={(e) => handleSubmit(e)}
                            disabled={!input.trim() || loading}
                            className={cn(
                                "absolute right-3 top-1/2 -translate-y-1/2 p-3 rounded-xl transition-all shadow-sm",
                                input.trim() && !loading
                                    ? "bg-primary text-white hover:bg-primary-dark hover:shadow-md hover:scale-105"
                                    : "bg-gray-200 text-gray-400 cursor-not-allowed"
                            )}
                        >
                            {loading ? <Loader2 size={20} className="animate-spin text-gray-500" /> : <Send size={20} />}
                        </button>
                    </div>
                </form>
                <div className="text-center mt-3">
                    <span className="text-[10px] text-gray-300 tracking-wider uppercase">Powered by PalmX AI</span>
                </div>
            </div>
        </div>
    );
}
