"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SignOutButton } from "@clerk/nextjs";
import { cn } from "@/lib/utils";

interface NavigationMenuProps {
    menuOpen: boolean;
    setMenuOpen: (open: boolean) => void;
}

export default function NavigationMenu({ menuOpen, setMenuOpen }: NavigationMenuProps) {
    const pathname = usePathname();
    
    return (
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
                        ].map((item, i) => {
                            const isActive = pathname === item.href;
                            return (
                                <Link
                                    key={item.label}
                                    href={item.href}
                                    onClick={() => setMenuOpen(false)}
                                    className={cn(
                                        "font-serif text-4xl md:text-6xl transition-all duration-500 transform hover:translate-x-4",
                                        isActive ? "text-gray-500" : "text-white/90 hover:text-primary",
                                        menuOpen ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
                                    )}
                                    style={{ transitionDelay: `${150 + (i * 100)}ms` }}
                                >
                                    {item.label}
                                </Link>
                            );
                        })}

                        

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
                    <SignOutButton>
                            <button
                                onClick={() => setMenuOpen(false)}
                                className={cn(
                                    "font-serif text-2xl md:text-2xl text-white-500 text-left hover:text-primary transition-all duration-300 transform hover:translate-x-2",
                                    menuOpen ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
                                )}
                                style={{ transitionDelay: `${450}ms` }}
                            >
                                Sign Out
                            </button>
                        </SignOutButton>

                </div>
            </div>

            {/* Background Elements */}
            <div className="absolute -bottom-[20%] -right-[10%] w-[90vh] h-[90vh] bg-primary/10 blur-[150px] rounded-full pointer-events-none mix-blend-screen"></div>
            <div className="absolute top-0 left-0 w-full h-full bg-[url('/noise.png')] opacity-[0.03] pointer-events-none"></div>
        </div>
    );
}

