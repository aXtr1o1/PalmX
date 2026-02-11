"use client";

import { useState } from "react";
import { Download, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";

type Lead = {
    timestamp: string;
    name: string;
    phone: string;
    interest_projects: string;
    preferred_region: string;
    unit_type: string;
    budget_min: string;
    budget_max: string;
    purpose: string;
    timeline: string;
    lead_summary: string;
    tags: string;
};

export default function AdminPage() {
    const [password, setPassword] = useState("");
    const [authenticated, setAuthenticated] = useState(false);
    const [leads, setLeads] = useState<Lead[]>([]);
    const [error, setError] = useState("");

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const data = await api.getLeads(password);
            setLeads(data);
            setAuthenticated(true);
            setError("");
        } catch (err) {
            setError("Invalid password or connection error");
        }
    };

    const downloadExcel = () => {
        fetch('/admin-api/leads/export.xlsx', {
            headers: { 'x-admin-password': password }
        })
            .then(resp => {
                if (!resp.ok) throw new Error('Export failed');
                return resp.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `leads_export_${new Date().toISOString().split('T')[0]}.xlsx`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            })
            .catch(err => alert("Download failed"));
    };

    if (!authenticated) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-100 font-sans">
                <form onSubmit={handleLogin} className="bg-white p-8 rounded-xl shadow-lg w-full max-w-sm space-y-4 border border-gray-200">
                    <div className="flex justify-center mb-4">
                        <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
                            <ShieldAlert className="text-gray-500" size={24} />
                        </div>
                    </div>
                    <h2 className="text-center text-xl font-semibold text-gray-800">Admin Access</h2>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Enter Admin Password"
                        className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent outline-none transition-all"
                    />
                    {error && <p className="text-red-500 text-sm text-center">{error}</p>}
                    <button type="submit" className="w-full bg-black text-white p-3 rounded-lg font-medium hover:bg-gray-800 transition-colors">
                        Access Dashboard
                    </button>
                </form>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 p-8 font-sans">
            <div className="max-w-7xl mx-auto space-y-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">PalmX Leads Dashboard</h1>
                        <p className="text-sm text-gray-500">Real-time lead capture monitoring</p>
                    </div>
                    <button
                        onClick={downloadExcel}
                        className="flex items-center space-x-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors shadow-sm"
                    >
                        <Download size={18} />
                        <span>Export Excel</span>
                    </button>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm whitespace-nowrap">
                            <thead className="bg-gray-50 border-b border-gray-200">
                                <tr>
                                    <th className="p-4 font-semibold text-gray-600">Time</th>
                                    <th className="p-4 font-semibold text-gray-600">Name</th>
                                    <th className="p-4 font-semibold text-gray-600">Contact</th>
                                    <th className="p-4 font-semibold text-gray-600">Summary</th>
                                    <th className="p-4 font-semibold text-gray-600">Projects</th>
                                    <th className="p-4 font-semibold text-gray-600">Details</th>
                                    <th className="p-4 font-semibold text-gray-600">Timeline</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {leads.map((l, i) => (
                                    <tr key={i} className="hover:bg-gray-50 transition-colors">
                                        <td className="p-4 text-gray-500 font-mono text-xs whitespace-nowrap">{new Date(l.timestamp).toLocaleString()}</td>
                                        <td className="p-4 font-medium text-gray-900">{l.name}</td>
                                        <td className="p-4">
                                            <div className="text-gray-900 font-mono">{l.phone}</div>
                                        </td>
                                        <td className="p-4 max-w-xs truncate text-gray-600" title={l.lead_summary}>
                                            {l.lead_summary || '-'}
                                        </td>
                                        <td className="p-4 text-gray-600 max-w-xs truncate" title={l.interest_projects}>
                                            {l.interest_projects}
                                            {l.preferred_region && <div className="text-xs text-gray-400">{l.preferred_region}</div>}
                                        </td>
                                        <td className="p-4 text-xs space-y-1">
                                            <div><span className="font-semibold">Unit:</span> {l.unit_type || '-'}</div>
                                            <div><span className="font-semibold">Budget:</span> {l.budget_min && l.budget_max ? `${l.budget_min} - ${l.budget_max}` : (l.budget_min || l.budget_max || '-')}</div>
                                            <div><span className="font-semibold">Purpose:</span> {l.purpose || '-'}</div>
                                        </td>
                                        <td className="p-4 text-gray-600 text-xs">
                                            {l.timeline || '-'}
                                        </td>
                                    </tr>
                                ))}
                                {leads.length === 0 && (
                                    <tr>
                                        <td colSpan={7} className="p-12 text-center text-gray-400">
                                            No leads captured yet. Start a chat session to generate data.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
