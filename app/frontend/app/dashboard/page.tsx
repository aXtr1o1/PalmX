"use client";

import React, { useState, useEffect } from 'react';
import { Download, Search, Filter, Lock } from 'lucide-react';

export default function Dashboard() {
    const [leads, setLeads] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [password, setPassword] = useState('');
    const [authenticated, setAuthenticated] = useState(false);
    const [error, setError] = useState('');

    // Filters
    const [search, setSearch] = useState('');
    const [regionFilter, setRegionFilter] = useState('All');

    const fetchLeads = async (pwd: string) => {
        setLoading(true);
        setError('');
        try {
            const res = await fetch('http://localhost:8000/admin/leads', {
                headers: { 'x-admin-password': pwd }
            });
            if (res.status === 401) {
                setError('Invalid password');
                setAuthenticated(false);
            } else if (res.ok) {
                const data = await res.json();
                setLeads(data);
                setAuthenticated(true);
                localStorage.setItem('adminKey', pwd);
            } else {
                setError('Failed to fetch leads');
            }
        } catch (e) {
            setError('Connection error');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const stored = localStorage.getItem('adminKey');
        if (stored) {
            setPassword(stored);
            fetchLeads(stored);
        }
    }, []);

    const handleLogin = (e: React.FormEvent) => {
        e.preventDefault();
        fetchLeads(password);
    };

    const handleExport = () => {
        window.open(`http://localhost:8000/admin/leads/export.xlsx?x-admin-password=${password}`, '_blank');
    };

    const filteredLeads = leads.filter(l => {
        const matchesSearch = l.name?.toLowerCase().includes(search.toLowerCase()) ||
            l.phone?.includes(search) ||
            l.interest_projects?.some((p: string) => p.toLowerCase().includes(search.toLowerCase()));

        const matchesRegion = regionFilter === 'All' || l.preferred_region === regionFilter;

        return matchesSearch && matchesRegion;
    });

    if (!authenticated) {
        return (
            <div className="min-h-screen bg-white flex flex-col items-center justify-center p-4">
                <div className="w-full max-w-md space-y-8 text-center animate-in fade-in slide-in-from-bottom-4 duration-700">
                    <div className="flex flex-col items-center gap-2">
                        <div className="w-16 h-16 bg-black rounded-full flex items-center justify-center text-white font-serif text-xl border border-gray-100 shadow-xl">PH</div>
                        <h1 className="font-serif text-2xl tracking-widest mt-4">PALM HILLS</h1>
                        <p className="text-xs uppercase tracking-[0.3em] text-gray-400">Concierge Dashboard</p>
                    </div>

                    <form onSubmit={handleLogin} className="space-y-4">
                        <div className="relative">
                            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                            <input
                                type="password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="Enter Access Code"
                                className="w-full pl-12 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-full focus:outline-none focus:border-black transition-all text-center tracking-widest text-sm"
                            />
                        </div>
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3 bg-black text-white rounded-full text-xs font-bold tracking-widest uppercase hover:bg-primary transition-colors disabled:opacity-50"
                        >
                            {loading ? 'Verifying...' : 'Access Safe'}
                        </button>
                    </form>
                    {error && <p className="text-red-500 text-xs tracking-wide">{error}</p>}
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#FDFDFD] text-foreground font-sans selection:bg-black selection:text-white">
            {/* Header */}
            <header className="fixed top-0 w-full bg-white/95 backdrop-blur-md z-40 border-b border-gray-100 px-6 md:px-12 h-[88px] flex items-center justify-between transition-all">
                <div className="flex items-center gap-6">
                    <div className="w-10 h-10 bg-black rounded-full flex items-center justify-center text-white font-serif text-xs border-2 border-white shadow-lg">PH</div>
                    <div className="hidden md:flex flex-col">
                        <span className="font-serif text-lg tracking-widest font-bold text-black">PALM HILLS</span>
                        <span className="text-[9px] uppercase tracking-[0.3em] text-accent font-medium">Concierge Admin</span>
                    </div>
                </div>
                <div className="flex items-center gap-6">
                    <button
                        onClick={handleExport}
                        className="flex items-center gap-3 px-6 py-3 bg-black text-white hover:bg-primary rounded-full text-[10px] font-bold tracking-[0.15em] transition-all shadow-md hover:shadow-lg uppercase"
                    >
                        <Download size={12} />
                        Export Data
                    </button>
                    <div className="w-px h-6 bg-gray-200"></div>
                    <button
                        onClick={() => {
                            setAuthenticated(false);
                            localStorage.removeItem('adminKey');
                        }}
                        className="text-[10px] font-bold text-gray-400 hover:text-black tracking-[0.2em] uppercase transition-colors"
                    >
                        Sign Out
                    </button>
                </div>
            </header>

            {/* Main Content */}
            <main className="pt-32 px-6 md:px-12 pb-12 max-w-[1600px] mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">

                {/* Stats / Intro */}
                <div className="mb-12">
                    <h1 className="font-serif text-3xl md:text-4xl text-black mb-2">Lead Intelligence</h1>
                    <p className="text-gray-500 font-light text-lg">Real-time concierge data analytics.</p>
                </div>

                {/* Filters */}
                <div className="flex flex-col md:flex-row gap-6 mb-8 justify-between items-end md:items-center bg-white p-6 rounded-3xl border border-gray-100 shadow-sm">
                    <div className="flex items-center gap-2 w-full md:w-auto flex-1">
                        <div className="relative w-full max-w-md">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-300" size={16} />
                            <input
                                type="text"
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                placeholder="Search leads..."
                                className="w-full pl-12 pr-4 py-3 bg-gray-50 border border-transparent hover:border-gray-200 focus:border-black rounded-xl text-sm transition-all outline-none"
                            />
                        </div>
                    </div>
                    <div className="flex gap-2 p-1 bg-gray-50 rounded-lg">
                        {['All', 'West', 'East', 'Coast'].map(r => (
                            <button
                                key={r}
                                onClick={() => setRegionFilter(r)}
                                className={`px-6 py-2 rounded-md text-xs font-medium transition-all ${regionFilter === r ? 'bg-white text-black shadow-sm' : 'bg-transparent text-gray-400 hover:text-gray-600'}`}
                            >
                                {r}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Table */}
                <div className="rounded-3xl border border-gray-100 overflow-hidden shadow-xl shadow-gray-100/50 bg-white">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <thead className="bg-surface/30 text-[10px] uppercase tracking-wider text-gray-500 font-medium">
                                <tr>
                                    <th className="px-6 py-4 font-medium">Name</th>
                                    <th className="px-6 py-4 font-medium">Contact</th>
                                    <th className="px-6 py-4 font-medium">Interest</th>
                                    <th className="px-6 py-4 font-medium">Budget</th>
                                    <th className="px-6 py-4 font-medium">Status/Timeline</th>
                                    <th className="px-6 py-4 font-medium">Tags</th>
                                    <th className="px-6 py-4 font-medium text-right">Date</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {filteredLeads.map((lead) => (
                                    <tr key={lead.lead_id} className="hover:bg-surface/30 transition-colors group">
                                        <td className="px-6 py-4">
                                            <div className="font-medium text-sm text-foreground">{lead.name}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="text-sm font-mono text-gray-600">{lead.phone}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="text-sm text-foreground">{lead.interest_projects?.join(', ') || '-'}</div>
                                            <div className="text-[10px] text-gray-400 mt-1">{lead.unit_type} • {lead.preferred_region}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="text-sm text-gray-600">
                                                {lead.budget_min ? `${(lead.budget_min / 1000000).toFixed(1)}M` : '0'}
                                                -
                                                {lead.budget_max ? `${(lead.budget_max / 1000000).toFixed(1)}M` : '?'}
                                            </div>
                                            <div className="text-[10px] text-gray-400 mt-1 uppercase">{lead.purpose}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="inline-flex items-center px-2 py-1 rounded-full text-[10px] font-medium bg-green-50 text-green-700">
                                                {lead.next_step}
                                            </span>
                                            <div className="text-[10px] text-gray-400 mt-1 pl-1">{lead.timeline}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-wrap gap-1">
                                                {lead.tags?.slice(0, 3).map((t: string) => (
                                                    <span key={t} className="px-1.5 py-0.5 bg-gray-100 rounded text-[9px] text-gray-500 border border-gray-200">
                                                        {t}
                                                    </span>
                                                ))}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="text-xs text-gray-400">
                                                {new Date(lead.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                                            </div>
                                            <div className="text-[9px] text-gray-300 mt-0.5">
                                                {new Date(lead.created_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {filteredLeads.length === 0 && (
                        <div className="p-12 text-center text-gray-400 text-sm font-light">
                            No leads found matching your criteria.
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
