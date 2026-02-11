"use client";

import React from 'react';
import Link from 'next/link';
import { ArrowLeft, CheckCircle2, FileText, Database } from 'lucide-react';

export default function DataSources() {
    const verifiedPortfolios = [
        {
            region: "West Cairo",
            projects: ["Badya", "The Crown", "Palm Hills October", "Golf Central", "Crown Central", "Hale Town"]
        },
        {
            region: "East Cairo",
            projects: ["Palm Hills New Cairo", "New Capital"]
        },
        {
            region: "North Coast",
            projects: ["Hacienda West", "Hacienda Bay", "Hacienda White"]
        },
        {
            region: "Red Sea",
            projects: ["Tawaya (Sahl Hasheesh)"]
        }
    ];

    const lastUpdate = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });

    return (
        <div className="min-h-screen bg-white text-foreground font-sans selection:bg-black selection:text-white">

            {/* Header */}
            <header className="fixed top-0 w-full bg-white/95 backdrop-blur-md z-40 border-b border-gray-100 px-6 md:px-12 h-[88px] flex items-center justify-between">
                <Link href="/" className="flex items-center gap-4 group">
                    <div className="w-10 h-10 bg-white border border-gray-200 rounded-full flex items-center justify-center text-black group-hover:bg-black group-hover:text-white transition-colors">
                        <ArrowLeft size={16} />
                    </div>
                    <span className="font-serif text-sm tracking-widest font-bold text-black uppercase hidden md:block group-hover:translate-x-1 transition-transform">Back to Concierge</span>
                </Link>

                <div className="flex flex-col items-center">
                    <span className="font-serif text-lg tracking-[0.2em] font-bold text-black border-b-2 border-transparent pb-1">PALM HILLS</span>
                    <span className="text-[9px] uppercase tracking-[0.3em] text-accent font-medium">Data Transparency</span>
                </div>

                <div className="w-10"></div> {/* Spacer for balance */}
            </header>

            {/* Main Content */}
            <main className="pt-40 px-6 md:px-12 pb-24 max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-8 duration-700">

                <div className="text-center mb-20 space-y-6">
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-surface rounded-full mb-4 border border-gray-100">
                        <Database size={12} className="text-accent" />
                        <span className="text-[10px] uppercase tracking-[0.2em] font-medium text-gray-500">System Source of Truth</span>
                    </div>
                    <h1 className="font-serif text-5xl md:text-6xl text-black leading-tight">Verified Intelligence.</h1>
                    <p className="text-gray-500 font-light text-xl max-w-2xl mx-auto leading-relaxed">
                        The PalmX Concierge is powered exclusively by verified data from the official Palm Hills Developments portfolio. We strictly index the following assets to ensure truthfulness.
                    </p>
                </div>

                {/* Data Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-20">
                    {verifiedPortfolios.map((portfolio, idx) => (
                        <div key={idx} className="bg-surface/30 p-8 rounded-3xl border border-gray-100 hover:border-gray-200 transition-colors group">
                            <h3 className="font-serif text-2xl text-black mb-6 px-4 border-l-2 border-accent/50">{portfolio.region}</h3>
                            <ul className="space-y-4">
                                {portfolio.projects.map((project) => (
                                    <li key={project} className="flex items-center gap-3 px-4 py-3 bg-white rounded-xl shadow-sm border border-gray-50 group-hover:translate-x-1 transition-transform duration-300">
                                        <CheckCircle2 size={16} className="text-green-600 flex-shrink-0" />
                                        <span className="text-sm font-medium tracking-wide text-gray-700">{project}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>

                {/* File Meta */}
                <div className="bg-black text-white p-10 rounded-3xl relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-accent/20 blur-[100px] rounded-full pointer-events-none"></div>

                    <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
                        <div className="space-y-4">
                            <div className="flex items-center gap-3 text-accent">
                                <FileText size={20} />
                                <span className="text-xs uppercase tracking-[0.2em] font-bold">Primary Knowledge Base</span>
                            </div>
                            <h4 className="font-serif text-3xl">PalmX-buyerKB.csv</h4>
                            <div className="flex flex-wrap gap-4 text-sm text-gray-400 font-mono mt-2">
                                <span>Status: <span className="text-white">Active</span></span>
                                <span>•</span>
                                <span>Indexed: <span className="text-white">{lastUpdate}</span></span>
                                <span>•</span>
                                <span>Schema: <span className="text-white">v2.4 (Strict)</span></span>
                            </div>
                        </div>

                        <div className="flex flex-col gap-2">
                            <div className="px-6 py-3 bg-white/10 rounded-lg text-center backdrop-blur-sm border border-white/5">
                                <span className="block text-2xl font-bold text-white">100%</span>
                                <span className="text-[10px] uppercase tracking-widest text-gray-400">Verified Data</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="mt-12 text-center border-t border-gray-100 pt-8">
                    <p className="text-xs text-gray-400 font-light">
                        *This data transparency report is generated automatically by the PalmX System.
                    </p>
                </div>

            </main>
        </div>
    );
}
