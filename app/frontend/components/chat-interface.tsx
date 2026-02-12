"use client";

import { useEffect, useState, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
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
    const [menuOpen, setMenuOpen] = useState(false);

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
            <div className="flex flex-col h-screen w-full bg-white relative items-center justify-center">
                <div className="flex flex-col items-center space-y-8 max-w-sm w-full p-8">
                    <Image
                        src="/brand/palmHills-BlockLogo.png"
                        alt="Palm Hills"
                        width={80}
                        height={80}
                        className="opacity-80"
                    />
                    <div className="text-center space-y-2">
                        <h2 className="font-serif text-2xl text-[#0B0B0B] tracking-tight">Initializing PalmX</h2>
                        <p className="text-sm text-[#5A5A5A] font-light">Loading verified market data...</p>
                    </div>
                    <div className="w-full h-1 bg-[#E9E9E9] rounded-full overflow-hidden">
                        <div
                            className="h-full bg-[#D22048] transition-all duration-500 ease-out rounded-full"
                            style={{ width: `${bootProgress}%` }}
                        />
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-screen w-full bg-white relative animate-in fade-in duration-700 font-sans text-foreground">

            {/* Palm Hills Global Shell */}
            <header className="fixed top-0 left-0 w-full bg-white/95 backdrop-blur-md z-50 h-[88px] flex items-center justify-between px-6 md:px-12 border-b border-gray-100 transition-all duration-300">
                {/* Left: Menu */}
                <div className="flex items-center gap-6">
                    <button
                        onClick={() => setMenuOpen(true)}
                        className="group flex flex-col gap-1.5 w-8 hover:opacity-70 transition-opacity p-2 -ml-2"
                    >
                        <span className="w-8 h-0.5 bg-black group-hover:bg-primary transition-colors"></span>
                        <span className="w-5 h-0.5 bg-black group-hover:bg-primary transition-colors"></span>
                        <span className="w-8 h-0.5 bg-black group-hover:bg-primary transition-colors"></span>
                    </button>
                    {/* Search Bar Removed as per user request (useless) */}
                </div>

                {/* Center: Logo */}
                <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 mt-1">
                    <div className="flex flex-col items-center">
                        <Image
                            src="/brand/PalmHills-Logo.png"
                            alt="Palm Hills"
                            width={160}
                            height={42}
                            className="object-contain mb-1"
                        />
                        <span className="text-[9px] uppercase tracking-[0.3em] text-[#5A5A5A] font-medium">PALMX AI</span>
                    </div>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-8">
                    <span className="hidden md:block font-sans text-xs font-bold tracking-widest text-black">19743</span>
                    <span className="hidden md:block w-px h-4 bg-gray-200"></span>
                    <span className="hidden md:block font-sans text-xs font-bold text-muted cursor-pointer hover:text-black tracking-widest">عربي</span>
                    <button className="hidden lg:flex bg-black text-white px-8 py-3 rounded-full text-[10px] font-bold tracking-[0.2em] hover:bg-primary hover:scale-105 transition-all uppercase shadow-lg shadow-black/5">
                        Request Sales Call
                    </button>
                </div>
            </header>

            {/* Menu Overlay */}
            <div className={cn(
                "fixed inset-0 bg-[#0B0B0B] z-[100] transition-all duration-700 ease-[cubic-bezier(0.87,0,0.13,1)] overflow-hidden",
                menuOpen ? "translate-y-0 opacity-100 visible" : "-translate-y-full opacity-0 invisible pointer-events-none"
            )}>
                {/* Close Button */}
                <div className="absolute top-6 right-6 md:top-8 md:right-12 z-[110]">
                    <button onClick={() => setMenuOpen(false)} className="text-white hover:text-primary transition-colors p-2 group">
                        <span className="sr-only">Close</span>
                        <div className="relative w-6 h-6 flex items-center justify-center">
                            <span className="absolute w-6 h-0.5 bg-current rotate-45 transform origin-center transition-transform duration-300 group-hover:rotate-90"></span>
                            <span className="absolute w-6 h-0.5 bg-current -rotate-45 transform origin-center transition-transform duration-300 group-hover:rotate-0"></span>
                        </div>
                    </button>
                </div>

                {/* Palm Hills Logo in Overlay */}
                <div className={cn(
                    "absolute top-8 left-8 md:left-12 z-[110] transition-all duration-1000 delay-200",
                    menuOpen ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-4"
                )}>
                    <div className="flex flex-col">
                        <span className="font-serif text-2xl tracking-[0.2em] font-bold text-white">PALM HILLS</span>
                        <span className="text-[9px] uppercase tracking-[0.4em] text-primary/80 font-medium mt-1">Developments</span>
                    </div>
                </div>

                <div className="h-full w-full max-w-[1400px] mx-auto px-6 md:px-12 flex flex-col md:flex-row relative z-10 pt-32 pb-12">

                    {/* Left Column: Navigation */}
                    <div className="flex-1 flex flex-col justify-center space-y-8 md:border-r border-white/10 md:pr-12">
                        <nav className="flex flex-col space-y-6">
                            {[
                                { label: 'Concierge', href: '/' },
                                { label: 'Dashboard', href: '/dashboard' },
                                { label: 'Data Sources', href: '/data-sources' },
                            ].map((item, i) => (
                                <Link
                                    key={item.label}
                                    href={item.href}
                                    onClick={() => setMenuOpen(false)}
                                    className={cn(
                                        "font-serif text-4xl md:text-6xl text-white/90 hover:text-primary transition-all duration-500 transform hover:translate-x-4",
                                        menuOpen ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
                                    )}
                                    style={{ transitionDelay: `${150 + (i * 100)}ms` }}
                                >
                                    {item.label}
                                </Link>
                            ))}

                            <div className="pt-8 mt-4 border-t border-white/10 w-24"></div>

                            <div className={cn(
                                "space-y-5 transition-all duration-700 delay-[450ms]",
                                menuOpen ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
                            )}>
                                <h4 className="text-[10px] font-bold tracking-[0.3em] uppercase text-white/60">POC Scope</h4>
                                <ul className="space-y-3">
                                    {[
                                        'AI concierge trained on verified Palm Hills portfolio',
                                        'Lead capture with structured buyer-intent data',
                                        'Real-time analytics dashboard with export',
                                        'RAG-powered retrieval from official listings',
                                    ].map((item, i) => (
                                        <li key={i} className="flex items-start gap-3">
                                            <span className="w-1.5 h-1.5 rounded-full bg-primary/60 mt-2 flex-shrink-0" />
                                            <span className="text-sm font-light text-white/50">{item}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </nav>
                    </div>

                    {/* Right Column: Information & Disclaimer */}
                    <div className="flex-1 flex flex-col justify-center md:pl-16 space-y-12 text-white/80 mt-12 md:mt-0">

                        <div className={cn(
                            "space-y-6 transition-all duration-700 delay-[600ms]",
                            menuOpen ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
                        )}>
                            <div className="w-12 h-1 bg-primary mb-6"></div>
                            <h3 className="text-xs font-bold tracking-[0.4em] uppercase text-white mb-2">The Concierge System</h3>
                            <p className="font-light leading-relaxed text-lg max-w-md text-white/70">
                                Experience a new standard of property discovery. Our AI Concierge is exclusively trained on the verified Palm Hills portfolio, ensuring accuracy, privacy, and seamless guidance.
                            </p>
                        </div>

                        <div className={cn(
                            "space-y-6 transition-all duration-700 delay-[700ms]",
                            menuOpen ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
                        )}>
                            <div className="grid grid-cols-2 gap-8">
                                <div>
                                    <h4 className="text-[10px] font-bold tracking-[0.2em] uppercase text-primary mb-2">Data Integrity</h4>
                                    <p className="text-sm font-light text-white/50">
                                        Sourced directly from official active listings.
                                    </p>
                                </div>
                                <div>
                                    <h4 className="text-[10px] font-bold tracking-[0.2em] uppercase text-primary mb-2">System Scope</h4>
                                    <p className="text-sm font-light text-white/50">
                                        Proof of Concept (POC) v1.0. <br /> Future: Voice & Real-time CRM.
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className={cn(
                            "pt-12 border-t border-white/10 flex flex-col gap-2 transition-all duration-700 delay-[800ms]",
                            menuOpen ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
                        )}>
                            <p className="text-[10px] uppercase tracking-[0.25em] text-white/40">
                                Crafted by <a href="https://cloudgate.ae/" target="_blank" className="text-white hover:text-primary transition-colors border-b border-white/20 pb-0.5 hover:border-primary">CloudGate</a>
                            </p>
                            <p className="text-[10px] uppercase tracking-[0.25em] text-white/20">
                                © {new Date().getFullYear()} Palm Hills Developments.
                            </p>
                        </div>

                    </div>
                </div>

                {/* Background Elements */}
                <div className="absolute -bottom-[20%] -right-[10%] w-[90vh] h-[90vh] bg-primary/10 blur-[150px] rounded-full pointer-events-none mix-blend-screen"></div>
                <div className="absolute top-0 left-0 w-full h-full bg-[url('/noise.png')] opacity-[0.03] pointer-events-none"></div>
            </div>

            {/* Spacer */}
            <div className="h-[88px] flex-shrink-0"></div>

            {/* Chat Area */}
            <div className="flex-1 relative overflow-hidden flex flex-col max-w-[1400px] mx-auto w-full px-4 md:px-8">

                <div ref={scrollRef} className="flex-1 overflow-y-auto py-8 space-y-12 scroll-smooth no-scrollbar">

                    {/* Welcome State */}
                    {messages.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-[70vh] space-y-12 opacity-0 animate-in fade-in slide-in-from-bottom-8 duration-1000 fill-mode-forwards">
                            {/* Premium Brand Glyph */}
                            <div className="w-24 h-24 rounded-full border border-gray-100 flex items-center justify-center mb-4 bg-white shadow-xl shadow-gray-100/50 overflow-hidden p-4">
                                <Image
                                    src="/brand/palmHills-BlockLogo.png"
                                    alt="PalmX"
                                    width={80}
                                    height={80}
                                    className="object-contain"
                                />
                            </div>

                            <div className="text-center max-w-2xl space-y-6">
                                <h2 className="font-serif text-5xl md:text-6xl text-black leading-tight tracking-tight">
                                    The Art of Living
                                </h2>
                                <p className="text-muted font-light leading-relaxed text-lg md:text-xl max-w-lg mx-auto">
                                    I am <span className="text-black font-medium">PalmX</span>. Your private concierge for Palm Hills.
                                    Looking for a villa in the West or a chalet by the sea?
                                </p>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-3xl mt-12 px-4">
                                {QUICK_PROMPTS.map((p, i) => (
                                    <button
                                        key={i}
                                        onClick={() => handleSubmit(undefined, p)}
                                        className="px-8 py-5 bg-white border border-gray-100 hover:border-black rounded-xl text-center text-sm text-gray-600 transition-all hover:shadow-lg hover:-translate-y-1 group flex flex-col items-center justify-center gap-3 h-32"
                                    >
                                        <span className="w-8 h-8 rounded-full bg-surface flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-colors">
                                            <ArrowRight size={12} />
                                        </span>
                                        <span className="font-medium tracking-wide uppercase text-xs">{p}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Messages */}
                    {messages.map((m, i) => (
                        <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} group max-w-5xl mx-auto w-full animate-in fade-in slide-in-from-bottom-2 duration-500`}>

                            {m.role === 'assistant' && (
                                <div className="w-10 h-10 rounded-full bg-white flex-shrink-0 flex items-center justify-center mr-4 mt-1 border border-gray-100 shadow-sm overflow-hidden p-1.5">
                                    <Image
                                        src="/brand/palmHills-BlockLogo.png"
                                        alt="PalmX"
                                        width={40}
                                        height={40}
                                        className="object-contain opacity-90"
                                    />
                                </div>
                            )}

                            <div className={cn(
                                "max-w-[85%] md:max-w-[70%] px-8 py-6 text-base leading-7 relative shadow-sm",
                                m.role === 'user'
                                    ? "bg-[#D22048] text-white rounded-3xl rounded-tr-sm"
                                    : "bg-white text-gray-800 border border-gray-50 rounded-3xl rounded-tl-sm shadow-[0_2px_20px_-5px_rgba(0,0,0,0.05)]"
                            )}>
                                {m.role === 'user' ? (
                                    <div className="whitespace-pre-wrap font-light tracking-wide">{m.content}</div>
                                ) : (
                                    <div className="font-light tracking-wide text-[15px]">
                                        <ReactMarkdown
                                            components={{
                                                h1: ({ node, ...props }: any) => (
                                                    <h1 className="font-serif text-3xl text-[#5A5A5A] mt-8 mb-4 tracking-wide" {...props} />
                                                ),
                                                h2: ({ node, ...props }: any) => (
                                                    <h2 className="font-serif text-2xl text-[#5A5A5A] mt-8 mb-4 tracking-wide" {...props} />
                                                ),
                                                h3: ({ node, ...props }: any) => (
                                                    <h3 className="font-serif text-xl text-[#5A5A5A] mt-8 mb-4 tracking-wide border-b border-gray-100 pb-2" {...props} />
                                                ),
                                                h4: ({ node, ...props }: any) => (
                                                    <h4 className="font-serif text-lg text-[#5A5A5A] mt-6 mb-3 tracking-wide" {...props} />
                                                ),
                                                p: ({ node, ...props }: any) => (
                                                    <p className="leading-7 mb-4 last:mb-0 text-gray-600" {...props} />
                                                ),
                                                ul: ({ node, ...props }: any) => (
                                                    <ul className="space-y-3 mb-6 mt-4" {...props} />
                                                ),
                                                li: ({ node, ...props }: any) => (
                                                    <li className="flex items-start gap-3" {...props}>
                                                        <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-accent mt-2.5" />
                                                        <span className="text-gray-700">{props.children}</span>
                                                    </li>
                                                ),
                                                strong: ({ node, ...props }: any) => (
                                                    <strong className="font-semibold text-[#D22048]" {...props} />
                                                ),
                                                a: ({ node, ...props }: any) => (
                                                    <a className="text-accent hover:text-black border-b border-accent/20 hover:border-black transition-all pb-0.5 font-medium" {...props} target="_blank" rel="noopener noreferrer" />
                                                )
                                            }}
                                        >
                                            {m.content}
                                        </ReactMarkdown>
                                    </div>
                                )}
                                {m.role === 'assistant' && (
                                    <div className="absolute -bottom-6 left-0 opacity-0 group-hover:opacity-100 transition-opacity flex items-center space-x-2 text-[9px] text-muted uppercase tracking-[0.2em] mt-2 ml-1">
                                        <span>PalmX AI</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {/* Loading Indicator */}
                    {loading && (
                        <div className="flex justify-start max-w-5xl mx-auto w-full">
                            <div className="w-10 h-10 rounded-full bg-white flex-shrink-0 flex items-center justify-center mr-4 mt-1 border border-gray-100 overflow-hidden p-1.5">
                                <Image
                                    src="/brand/palmHills-BlockLogo.png"
                                    alt="PalmX"
                                    width={40}
                                    height={40}
                                    className="object-contain opacity-90"
                                />
                            </div>
                            <div className="bg-white px-8 py-5 rounded-3xl rounded-tl-sm flex items-center space-x-3 shadow-sm border border-gray-50">
                                <span className="text-xs uppercase tracking-widest text-gray-400 mr-2">Concierge Thinking</span>
                                <div className="flex space-x-1">
                                    <div className="w-1 h-1 bg-black rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                    <div className="w-1 h-1 bg-black rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                    <div className="w-1 h-1 bg-black rounded-full animate-bounce"></div>
                                </div>
                            </div>
                        </div>
                    )}

                    <div className="h-4"></div>
                </div>
            </div>

            {/* Input Area */}
            <div className="bg-white/90 backdrop-blur-md p-6 border-t border-gray-100 z-20">
                <form onSubmit={(e) => e.preventDefault()} className="relative max-w-3xl mx-auto">
                    <div className="relative group">
                        <div className="absolute top-1/2 -translate-y-1/2 left-4 text-xs font-bold tracking-widest text-accent uppercase pointer-events-none">
                            {mode === 'concierge' ? 'Concierge' : 'Assistance'}
                        </div>

                        <textarea
                            id="chat-input"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSubmit(e);
                                }
                            }}
                            autoComplete="off"
                            placeholder={mode === 'concierge' ? "Ask about availability and prices..." : "Please enter your details..."}
                            className="w-full pl-32 pr-12 py-4 bg-surface border border-transparent focus:border-gray-200 rounded-2xl focus:ring-0 focus:outline-none transition-all font-sans text-charcoal placeholder:text-muted/50 shadow-sm resize-none overflow-hidden min-h-[56px] max-h-[200px]"
                            rows={1}
                            style={{ height: 'auto', minHeight: '56px' }}
                            onInput={(e) => {
                                const target = e.target as HTMLTextAreaElement;
                                target.style.height = 'auto';
                                target.style.height = `${Math.min(target.scrollHeight, 200)}px`;
                            }}
                        />
                        <button
                            type="button"
                            onClick={(e) => handleSubmit(e)}
                            disabled={!input.trim() || loading}
                            className={cn(
                                "absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full transition-all",
                                input.trim() && !loading
                                    ? "bg-black text-white hover:bg-primary"
                                    : "bg-gray-200 text-gray-400 cursor-not-allowed"
                            )}
                        >
                            {loading ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
                        </button>
                    </div>
                </form>
            </div >
        </div >
    );
}
