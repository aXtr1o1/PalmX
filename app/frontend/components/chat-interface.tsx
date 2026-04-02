"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import Image from "next/image";
import { ArrowRight, Loader2, MapPin } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { api, ChatMessage, ProjectCard } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useApp } from "@/contexts/app-context";
import NavigationMenu from "./navigation-menu";

const SESSION_ID_KEY = "palmx_sess_id";

const QUICK_PROMPTS = [
    { label: "Villa in Badya starting 10M", description: "Explore luxury villas from 10M EGP" },
    { label: "Apartments in New Cairo", description: "Browse available units & layouts" },
    { label: "Payment plans for The Crown", description: "Flexible plans tailored for you" },
    { label: "Ready to move options", description: "Units available for immediate handover" },
];

// ---------------------------------------------------------------------------
// CardTile — gradient style matching user bubbles & CTA card.
// from-[#0B0B0B] via-[#6b0a1e] to-[#c01e3e], white text, decorative corner.
// Single Enquire Now button only — triggers chat, no external links.
// No outer onClick — only the button fires (prevents double-fire).
// ---------------------------------------------------------------------------
function CardTile({ card, onSelect }: { card: ProjectCard; onSelect: (c: ProjectCard) => void }) {
    return (
        <div className="relative rounded-2xl overflow-hidden w-full bg-gradient-to-tl from-[#0B0B0B] via-[#6b0a1e] to-[#c01e3e] shadow-lg shadow-black/20 border border-white/5">
            {/* Decorative corner — same as user bubble & quick prompts */}
            <div className="absolute bottom-0 left-0 w-20 h-20 bg-black/20 rounded-tr-full pointer-events-none" />

            <div className="relative z-10 p-4 flex flex-col gap-2">

                {/* Type + Status row */}
                <div className="flex items-center justify-between">
                    {card.type && (
                        <span className="text-[9px] uppercase tracking-[0.2em] font-semibold text-white/50">
                            {card.type}
                        </span>
                    )}
                    {card.status && (
                        <span className="text-[8px] uppercase tracking-widest font-medium text-white/70 bg-white/10 border border-white/10 px-1.5 py-0.5 rounded-full">
                            {card.status.replace(/_/g, " ")}
                        </span>
                    )}
                </div>

                {/* Title */}
                <h4 className="font-serif text-[15px] font-semibold text-white leading-tight tracking-wide">
                    {card.title}
                </h4>

                {/* Location */}
                {card.location && (
                    <div className="flex items-center gap-1 text-[11px] text-white/60">
                        <MapPin size={9} className="text-white/40 flex-shrink-0" />
                        <span className="truncate">{card.location}</span>
                    </div>
                )}

                {/* Price block */}
                <div className="border-t border-white/10 pt-2">
                    <p className="text-[8px] uppercase tracking-[0.2em] text-white/40 mb-0.5">Starting From</p>
                    <p className={cn(
                        "text-[14px] font-bold text-white",
                        !card.price && "italic text-[12px] font-normal text-white/50"
                    )}>
                        {card.price || "Pricing on request"}
                    </p>
                </div>

                {/* Amenity pills — max 2 to keep height compact */}
                {card.amenities && card.amenities.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                        {card.amenities.slice(0, 2).map((a, i) => (
                            <span key={i} className="text-[9px] text-white/70 border border-white/20 px-2 py-0.5 rounded-full">
                                {a}
                            </span>
                        ))}
                    </div>
                )}

                {/* Enquire Now */}
                <button
                    type="button"
                    onClick={() => onSelect(card)}
                    className="w-full mt-1 bg-white/10 hover:bg-white/20 border border-white/20 hover:border-white/40 text-white text-[10px] font-bold uppercase tracking-[0.15em] py-2 rounded-lg transition-all duration-200"
                >
                    Enquire Now
                </button>
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// ProjectCardsSlideshow
// - Shows 2 cards at a time with a peek of the next one
// - Native horizontal scroll: trackpad, touch, and mouse all work
// - Dot indicators sync via IntersectionObserver
// - Prev/next buttons scroll by one card width
// ---------------------------------------------------------------------------
function ProjectCardsSlideshow({
    cards,
    onSelect,
}: {
    cards: ProjectCard[];
    onSelect: (card: ProjectCard) => void;
}) {
    const [activeIndex, setActiveIndex] = useState(0);
    const scrollContainerRef = useRef<HTMLDivElement>(null);

    if (!cards || cards.length === 0) return null;

    // Sync dot indicator with scroll position via IntersectionObserver
    useEffect(() => {
        const container = scrollContainerRef.current;
        if (!container) return;

        const items = container.querySelectorAll("[data-card-index]");
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        const idx = parseInt((entry.target as HTMLElement).dataset.cardIndex || "0");
                        setActiveIndex(idx);
                    }
                });
            },
            { root: container, threshold: 0.6 }
        );

        items.forEach((item) => observer.observe(item));
        return () => observer.disconnect();
    }, [cards.length]);

    const scrollTo = (index: number) => {
        const container = scrollContainerRef.current;
        if (!container) return;
        const item = container.querySelector(`[data-card-index="${index}"]`) as HTMLElement;
        if (item) item.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "start" });
    };

    const prev = (e: React.MouseEvent) => {
        e.stopPropagation();
        scrollTo(Math.max(0, activeIndex - 1));
    };

    const next = (e: React.MouseEvent) => {
        e.stopPropagation();
        scrollTo(Math.min(cards.length - 1, activeIndex + 1));
    };

    return (
        <div className="mt-5 w-full">
            {/* Scroll container — native scroll, 2 cards visible + peek of 3rd */}
            <div
                ref={scrollContainerRef}
                className="flex gap-3 overflow-x-auto pb-1"
                style={{
                    scrollSnapType: "x mandatory",
                    WebkitOverflowScrolling: "touch",
                    scrollbarWidth: "none",
                    msOverflowStyle: "none",
                }}
            >
                <style>{`.cards-scroll::-webkit-scrollbar { display: none; }`}</style>
                {cards.map((card, i) => (
                    <div
                        key={card.id}
                        data-card-index={i}
                        style={{
                            scrollSnapAlign: "start",
                            flex: "0 0 calc(50% - 6px)",
                            minWidth: "calc(50% - 6px)",
                        }}
                    >
                        <CardTile card={card} onSelect={onSelect} />
                    </div>
                ))}
                {/* Trailing spacer so last card doesn't snap flush to edge */}
                <div style={{ flex: "0 0 8px", minWidth: "8px" }} />
            </div>

            {/* Dot indicators only — no arrows */}
            {cards.length > 1 && (
                <div className="flex justify-center gap-1.5 items-center mt-3">
                    {cards.map((_, i) => (
                        <button
                            key={i}
                            onClick={(e) => { e.stopPropagation(); scrollTo(i); }}
                            className={cn(
                                "rounded-full transition-all duration-200",
                                i === activeIndex ? "w-4 h-1.5 bg-[#D22048]" : "w-1.5 h-1.5 bg-gray-200 hover:bg-gray-400"
                            )}
                        />
                    ))}
                </div>
            )}

            <p className="text-[9px] uppercase tracking-[0.2em] text-gray-300 mt-2">
                Swipe or use arrows · Enquire to learn more
            </p>
        </div>
    );
}



export default function ChatInterface() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [sessionId, setSessionId] = useState("");
    const [mode, setMode] = useState<'concierge' | 'lead_capture'>('concierge');
    const { systemReady, bootProgress, setSystemReady, setBootProgress } = useApp();
    const [menuOpen, setMenuOpen] = useState(false);

    const scrollRef = useRef<HTMLDivElement>(null);
    const healthCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);
    // Prevents double-submit from rapid clicks or event bubbling
    const submittingRef = useRef(false);

    useEffect(() => {
        if (systemReady) return;
        const checkHealth = async () => {
            try {
                const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";
                const res = await fetch(backendUrl ? `${backendUrl}/api/health` : "/api/health");
                if (res.ok) {
                    setSystemReady(true);
                    setBootProgress(100);
                    if (healthCheckIntervalRef.current) { clearInterval(healthCheckIntervalRef.current); healthCheckIntervalRef.current = null; }
                } else {
                    setBootProgress((prev: number) => Math.min(prev + 10, 90));
                }
            } catch {
                setBootProgress((prev: number) => Math.min(prev + 5, 90));
            }
        };
        if (!healthCheckIntervalRef.current) healthCheckIntervalRef.current = setInterval(checkHealth, 1000);
        return () => { if (healthCheckIntervalRef.current) { clearInterval(healthCheckIntervalRef.current); healthCheckIntervalRef.current = null; } };
    }, [systemReady, setSystemReady, setBootProgress]);

    useEffect(() => {
        let sid = localStorage.getItem(SESSION_ID_KEY);
        if (!sid) { sid = Math.random().toString(36).substring(7); localStorage.setItem(SESSION_ID_KEY, sid); }
        setSessionId(sid);
    }, []);

    useEffect(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [messages, loading]);

    const handleSubmit = useCallback(async (e?: React.FormEvent, quickPrompt?: string) => {
        e?.preventDefault();
        const text = quickPrompt || input;
        if (!text.trim() || loading) return;

        // Guard: ignore if already mid-submit
        if (submittingRef.current) return;
        submittingRef.current = true;

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
                (token: string) => {
                    if (firstToken) {
                        firstToken = false;
                        setLoading(false);
                        setMessages(prev => [...prev, { role: "assistant", content: token }]);
                    } else {
                        setMessages(prev => {
                            const updated = [...prev];
                            const last = updated[updated.length - 1];
                            if (last?.role === "assistant") {
                                updated[updated.length - 1] = { ...last, content: last.content + token };
                            }
                            return updated;
                        });
                    }
                },
                (data) => {
                    // DEBUG — remove after cards confirmed working
                    console.log("[onDone] full data:", JSON.stringify(data));
                    console.log("[onDone] project_cards:", data.project_cards);
                    setMode(data.mode);
                    if (data.cta || data.cta_card || data.project_cards) {
                        setMessages(prev => {
                            const updated = [...prev];
                            const last = updated[updated.length - 1];
                            if (last?.role === "assistant") {
                                // Trim intro to 2 sentences when cards are present
                                let content = last.content;
                                if (data.trim_intro && data.project_cards?.length) {
                                    const sentences = content.match(/[^.!?]+[.!?]+/g) || [];
                                    content = sentences.slice(0, 2).join(" ").trim() || content;
                                }
                                updated[updated.length - 1] = {
                                    ...last,
                                    content,
                                    cta: data.cta,
                                    cta_card: data.cta_card,
                                    project_cards: data.project_cards,
                                    trim_intro: data.trim_intro,
                                };
                            }
                            return updated;
                        });
                    }
                }
            );
        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, { role: "assistant", content: "I'm having trouble connecting to PalmX. Please try again." }]);
        } finally {
            setLoading(false);
            // Release guard after short delay to absorb any bubble duplicates
            setTimeout(() => { submittingRef.current = false; }, 400);
        }
    }, [input, loading, messages, sessionId]);

    const handleCardSelect = useCallback((card: ProjectCard) => {
        handleSubmit(undefined, `Tell me more about ${card.title}`);
    }, [handleSubmit]);

    // -------------------------------------------------------------------------
    // Loading screen
    // -------------------------------------------------------------------------
    if (!systemReady) {
        return (
            <div className="flex flex-col h-screen w-full bg-white items-center justify-center">
                <div className="flex flex-col items-center space-y-8 max-w-sm w-full p-8">
                    <Image src="/brand/palmHills-BlockLogo.png" alt="Palm Hills" width={80} height={80} className="opacity-80" />
                    <div className="text-center space-y-2">
                        <h2 className="font-serif text-2xl text-[#0B0B0B] tracking-tight">Initializing PalmX</h2>
                        <p className="text-sm text-[#5A5A5A] font-light">Loading verified market data...</p>
                    </div>
                    <div className="w-full h-1 bg-[#E9E9E9] rounded-full overflow-hidden">
                        <div className="h-full bg-[#D22048] transition-all duration-500 ease-out rounded-full" style={{ width: `${bootProgress}%` }} />
                    </div>
                </div>
            </div>
        );
    }

    // -------------------------------------------------------------------------
    // Main UI
    // -------------------------------------------------------------------------
    return (
        <div className="flex flex-col h-screen w-screen bg-white relative animate-in fade-in duration-700 font-sans text-foreground">

            <header className="fixed top-0 left-0 w-full bg-white/95 backdrop-blur-md z-50 h-[88px] flex items-center justify-between px-6 md:px-12 border-b border-gray-100">
                <div className="flex items-center gap-6">
                    <button onClick={() => setMenuOpen(true)} className="group flex flex-col gap-1.5 w-8 hover:opacity-70 transition-opacity p-2 -ml-2">
                        <span className="w-8 h-0.5 bg-black group-hover:bg-primary transition-colors"></span>
                        <span className="w-5 h-0.5 bg-[#5A5A5A] group-hover:bg-primary transition-colors"></span>
                        <span className="w-8 h-0.5 bg-black group-hover:bg-primary transition-colors"></span>
                    </button>
                </div>

                <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 mt-1">
                    <div className="flex flex-col items-center">
                        <Image src="/brand/PalmHills-Logo.png" alt="Palm Hills" width={240} height={62} className="object-contain mb-1" />
                        <span className="text-[9px] uppercase tracking-[0.3em] text-[#5A5A5A] font-medium font-serif">PALMX AI</span>
                    </div>
                </div>

                <div className="flex items-center gap-8">
                    <span className="hidden md:block text-sm font-bold tracking-widest text-black">19743</span>
                    <span className="hidden md:block w-px h-4 bg-gray-200"></span>
                    <span className="hidden md:block text-xs font-bold text-muted cursor-pointer hover:text-black tracking-widest">عربي</span>
                    <div className="hidden lg:flex">
                        <a href="https://www.palmhillsdevelopments.com/en-us/interestedIn" target="_blank" rel="noopener noreferrer"
                            className="bg-black text-white px-8 py-3 rounded-full text-[11px] font-bold tracking-[0.2em] hover:bg-[#D22048] hover:scale-105 transition-all uppercase shadow-lg shadow-black/5">
                            Request a Sales Call
                        </a>
                    </div>
                </div>
            </header>

            <NavigationMenu menuOpen={menuOpen} setMenuOpen={setMenuOpen} />
            <div className="h-[88px] flex-shrink-0"></div>

            <div className="flex-1 relative overflow-hidden flex flex-col max-w-[1400px] mx-auto w-full px-4 md:px-8">

                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full space-y-12 animate-in fade-in slide-in-from-bottom-8 duration-1000">
                        <div className="text-center max-w-2xl space-y-6">
                            <h2 className="font-serif text-5xl md:text-6xl text-black leading-tight tracking-tight">The Art of Living</h2>
                            <p className="text-muted font-light leading-relaxed text-lg md:text-xl max-w-lg mx-auto">
                                I am <span className="text-black font-medium font-serif">PalmX</span>. Your private concierge for Palm Hills.
                                Looking for a villa in the West or a chalet by the sea?
                            </p>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full max-w-3xl">
                            {QUICK_PROMPTS.map((p, i) => (
                                <button key={i} onClick={() => handleSubmit(undefined, p.label)}
                                    className="relative px-5 py-5 bg-gradient-to-tl from-[#0B0B0B] via-[#6b0a1e] to-[#c01e3e] hover:from-[#1a1a1a] hover:via-[#7f0f22] hover:to-[#a8172a] hover:shadow-lg hover:shadow-black/30 border border-white/5 rounded-2xl text-left transition-all duration-200 hover:-translate-y-0.5 flex flex-col justify-start gap-1.5 h-28 overflow-hidden">
                                    <div className="absolute bottom-0 left-0 w-16 h-16 bg-black/20 rounded-tr-full" />
                                    <span className="font-serif text-[13px] font-semibold text-white leading-snug tracking-wide">{p.label}</span>
                                    <span className="text-[10px] text-white/60 font-light leading-snug">{p.description}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div ref={scrollRef} style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
                        className="flex-1 overflow-y-auto py-8 space-y-12 scroll-smooth [&::-webkit-scrollbar]:hidden">

                        {messages.map((m, i) => (
                            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} group max-w-5xl mx-auto w-full animate-in fade-in slide-in-from-bottom-2 duration-500`}>

                                {m.role === 'assistant' && (
                                    <div className="w-10 h-10 rounded-full bg-white flex-shrink-0 flex items-center justify-center mr-4 mt-1 border border-gray-100 shadow-sm overflow-hidden p-1.5">
                                        <Image src="/brand/palmHills-BlockLogo.png" alt="PalmX" width={40} height={40} className="object-contain opacity-90" />
                                    </div>
                                )}

                                <div className={cn(
                                    "px-8 py-6 text-base leading-7 relative shadow-sm",
                                    m.project_cards && m.project_cards.length > 0 ? "max-w-[96%] md:max-w-[88%]" : "max-w-[85%] md:max-w-[70%]",
                                    m.role === 'user'
                                        ? "bg-gradient-to-tl from-[#0B0B0B] via-[#6b0a1e] to-[#c01e3e] text-white rounded-3xl rounded-tr-sm shadow-lg shadow-black/20"
                                        : "bg-white text-gray-800 border border-gray-50 rounded-3xl rounded-tl-sm shadow-[0_2px_20px_-5px_rgba(0,0,0,0.05)]"
                                )}>
                                    {m.role === 'user' ? (
                                        <div className="whitespace-pre-wrap font-light tracking-wide">{m.content}</div>
                                    ) : (
                                        <div className="font-light tracking-wide text-[15px]">
                                            <ReactMarkdown components={{
                                                h1: ({ node, ...props }: any) => <h1 className="font-serif text-3xl text-[#5A5A5A] mt-8 mb-4 tracking-wide" {...props} />,
                                                h2: ({ node, ...props }: any) => <h2 className="font-serif text-2xl text-[#5A5A5A] mt-8 mb-4 tracking-wide" {...props} />,
                                                h3: ({ node, ...props }: any) => <h3 className="font-serif text-xl text-[#5A5A5A] mt-8 mb-4 tracking-wide border-b border-gray-100 pb-2" {...props} />,
                                                h4: ({ node, ...props }: any) => <h4 className="font-serif text-lg text-[#5A5A5A] mt-6 mb-3 tracking-wide" {...props} />,
                                                p: ({ node, ...props }: any) => <p className="leading-7 mb-4 last:mb-0 text-gray-600" {...props} />,
                                                ul: ({ node, ...props }: any) => <ul className="space-y-3 mb-6 mt-4" {...props} />,
                                                li: ({ node, ...props }: any) => (
                                                    <li className="flex items-start gap-3" {...props}>
                                                        <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-accent mt-2.5" />
                                                        <span className="text-gray-700">{props.children}</span>
                                                    </li>
                                                ),
                                                strong: ({ node, ...props }: any) => <strong className="font-semibold text-[#D22048]" {...props} />,
                                                a: ({ node, ...props }: any) => <a className="text-accent hover:text-black border-b border-accent/20 hover:border-black transition-all pb-0.5 font-medium" {...props} target="_blank" rel="noopener noreferrer" />,
                                            }}>
                                                {m.content}
                                            </ReactMarkdown>

                                            {/* Project cards — persists forever on this message */}
                                            {m.project_cards && m.project_cards.length > 0 && (
                                                <ProjectCardsSlideshow cards={m.project_cards} onSelect={handleCardSelect} />
                                            )}

                                            {m.cta && (
                                                <div className="mt-6">
                                                    <a href={m.cta.url || "#"} target="_blank" rel="noopener noreferrer"
                                                        className="inline-flex items-center gap-2 bg-black text-white px-5 py-2.5 rounded-full text-xs font-semibold tracking-widest hover:bg-[#D22048] transition-all">
                                                        {m.cta.label}<ArrowRight size={14} />
                                                    </a>
                                                </div>
                                            )}

                                            {m.cta_card && (
                                                <div className="mt-6">
                                                    <div className="relative px-5 py-5 bg-gradient-to-tl from-[#0B0B0B] via-[#6b0a1e] to-[#c01e3e] hover:shadow-lg hover:shadow-black/30 border border-white/5 rounded-2xl flex flex-col gap-3 min-h-[120px] overflow-hidden transition-all duration-200 hover:-translate-y-0.5">
                                                        <div className="absolute bottom-0 left-0 w-16 h-16 bg-black/20 rounded-tr-full" />
                                                        <span className="font-serif text-[13px] font-semibold text-white leading-snug tracking-wide z-10">{m.cta_card.title}</span>
                                                        {m.cta_card.price && <span className="text-[11px] text-white/70 font-light z-10">{m.cta_card.price}</span>}
                                                        {m.cta_card.actions && m.cta_card.actions.length > 0 && (
                                                            <div className="flex flex-wrap gap-2 mt-2 z-10">
                                                                {m.cta_card.actions.map((a, idx) => (
                                                                    <a key={idx} href={a.url || "#"} target="_blank" rel="noopener noreferrer"
                                                                        className="inline-flex items-center gap-2 bg-white text-black px-4 py-1.5 rounded-full text-[10px] font-semibold tracking-widest border border-gray-200 hover:border-black transition-all uppercase">
                                                                        {a.label}<ArrowRight size={12} />
                                                                    </a>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {m.role === 'assistant' && (
                                        <div className="absolute -bottom-6 left-0 opacity-0 group-hover:opacity-100 transition-opacity flex items-center space-x-2 text-[9px] text-muted uppercase tracking-[0.2em] mt-2 ml-1">
                                            <span className="font-serif">PalmX AI</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}

                        {loading && (
                            <div className="flex justify-start max-w-5xl mx-auto w-full">
                                <div className="w-10 h-10 rounded-full bg-white flex-shrink-0 flex items-center justify-center mr-4 mt-1 border border-gray-100 overflow-hidden p-1.5">
                                    <Image src="/brand/palmHills-BlockLogo.png" alt="PalmX" width={40} height={40} className="object-contain opacity-90" />
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
                )}

                <div className="bg-white/95 backdrop-blur-md w-screen p-4 md:p-6 border-t border-gray-100 pb-safe relative">
                    <form onSubmit={handleSubmit} className="relative max-w-3xl mx-auto flex gap-3 items-end">
                        <div className="relative flex-1 group">
                            <textarea
                                id="chat-input"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e as any); } }}
                                autoComplete="off"
                                placeholder={mode === 'concierge' ? "The journey to your dream starts here..." : "Please enter your details..."}
                                className="w-full pl-5 pr-16 py-3.5 bg-[#F3F4F6] border-0 focus:ring-1 focus:ring-gray-200 rounded-[24px] focus:outline-none transition-all font-sans text-[15px] text-[#0B0B0B] placeholder:text-gray-400 resize-none overflow-hidden min-h-[52px] max-h-[160px] leading-relaxed"
                                rows={1}
                                style={{ height: 'auto', minHeight: '52px' }}
                                onInput={(e) => {
                                    const target = e.target as HTMLTextAreaElement;
                                    target.style.height = 'auto';
                                    target.style.height = `${Math.min(target.scrollHeight, 160)}px`;
                                }}
                            />
                            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center -mt-0.5">
                                <button type="submit" disabled={!input.trim() || loading} aria-label="Send message"
                                    className={cn(
                                        "w-10 h-10 flex items-center justify-center rounded-full transition-all duration-200 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D22048]/30",
                                        input.trim() && !loading ? "bg-[#0B0B0B] text-white hover:bg-[#D22048] hover:scale-105 active:scale-95" : "bg-[#E9E9E9] text-[#9A9A9A] cursor-not-allowed"
                                    )}>
                                    {loading ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={20} />}
                                </button>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}