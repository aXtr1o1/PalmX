"use client";

import React, { useState, useEffect, useMemo } from "react";
import Image from "next/image";
import Link from "next/link";
import {
    Search,
    Download,
    FileSpreadsheet,
    ChevronDown,
    ChevronRight,
    X,
    Copy,
    ExternalLink,
    AlertCircle,
    RefreshCw,
    Users,
    TrendingUp,
    MapPin,
    Building2,
    Clock,
    DollarSign,
    Activity,
    Eye,
    Table2,
    BarChart3,
    FileText,
    ArrowUpDown,
} from "lucide-react";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    AreaChart,
    Area,
    PieChart,
    Pie,
    Cell,
} from "recharts";
import {
    adminApi,
    AnalyticsData,
    NormalizedLead,
    SheetInfo,
    SheetPreview,
    AuditData,
    HealthData,
} from "@/lib/admin-api";

// ---------------------------------------------------------------------------
// Brand palette
// ---------------------------------------------------------------------------
const ACCENT = "#D22048";
const CHART_COLORS = [
    "#0B0B0B",
    "#3A3A3A",
    "#5A5A5A",
    "#7A7A7A",
    "#9A9A9A",
    "#BABABA",
    "#D5D5D5",
    "#E9E9E9",
];
const CHART_ACCENT = [ACCENT, ...CHART_COLORS];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function fmtNum(n: number | null | undefined, fallback = "—"): string {
    if (n == null) return fallback;
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
    return n.toLocaleString();
}

function fmtDate(iso: string): string {
    if (!iso) return "—";
    try {
        const d = new Date(iso);
        return d.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
        });
    } catch {
        return iso;
    }
}

function fmtTime(iso: string): string {
    if (!iso) return "";
    try {
        return new Date(iso).toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
        });
    } catch {
        return "";
    }
}

// ---------------------------------------------------------------------------
// Component: KPI Card
// ---------------------------------------------------------------------------
function KpiCard({
    label,
    value,
    sub,
    icon: Icon,
    accent,
}: {
    label: string;
    value: string;
    sub?: string;
    icon: React.ElementType;
    accent?: boolean;
}) {
    return (
        <div className="bg-white border border-[#E9E9E9] rounded-2xl p-6 flex flex-col gap-3 min-w-0">
            <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-[#5A5A5A]">
                    {label}
                </span>
                <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center ${accent ? "bg-[#D22048]/10 text-[#D22048]" : "bg-[#FAFAFA] text-[#5A5A5A]"}`}
                >
                    <Icon size={14} />
                </div>
            </div>
            <div className="font-serif text-3xl text-[#0B0B0B] tracking-tight">
                {value}
            </div>
            {sub && (
                <p className="text-xs text-[#5A5A5A] font-light truncate">{sub}</p>
            )}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Component: Section Header
// ---------------------------------------------------------------------------
function SectionHeader({
    title,
    id,
    icon: Icon,
}: {
    title: string;
    id?: string;
    icon: React.ElementType;
}) {
    return (
        <div id={id} className="flex items-center gap-3 mb-6 scroll-mt-32">
            <div className="w-8 h-8 rounded-lg bg-[#FAFAFA] border border-[#E9E9E9] flex items-center justify-center text-[#5A5A5A]">
                <Icon size={14} />
            </div>
            <h2 className="font-serif text-2xl text-[#0B0B0B]">{title}</h2>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Component: Chart Card
// ---------------------------------------------------------------------------
function ChartCard({
    title,
    children,
}: {
    title: string;
    children: React.ReactNode;
}) {
    return (
        <div className="bg-white border border-[#E9E9E9] rounded-2xl p-6">
            <h3 className="text-[10px] font-bold tracking-[0.2em] uppercase text-[#5A5A5A] mb-4">
                {title}
            </h3>
            <div className="h-64">{children}</div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Component: LeadDetailDrawer
// ---------------------------------------------------------------------------
function LeadDetailDrawer({
    lead,
    onClose,
}: {
    lead: NormalizedLead;
    onClose: () => void;
}) {
    const [copied, setCopied] = useState(false);

    const copyJson = () => {
        navigator.clipboard.writeText(JSON.stringify(lead.raw, null, 2));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="fixed inset-0 z-50 flex justify-end">
            <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={onClose} />
            <div className="relative w-full max-w-lg bg-white shadow-2xl h-full overflow-y-auto animate-in slide-in-from-right duration-300">
                <div className="sticky top-0 bg-white/95 backdrop-blur-md border-b border-[#E9E9E9] px-6 py-4 z-10 flex items-center justify-between">
                    <h3 className="font-serif text-xl text-[#0B0B0B]">Lead Detail</h3>
                    <button
                        onClick={onClose}
                        className="w-8 h-8 rounded-full bg-[#FAFAFA] flex items-center justify-center hover:bg-[#E9E9E9] transition-colors"
                    >
                        <X size={14} />
                    </button>
                </div>

                <div className="p-6 space-y-6">
                    {/* Profile */}
                    <div className="space-y-4">
                        <div className="w-16 h-16 rounded-full bg-[#0B0B0B] flex items-center justify-center text-white font-serif text-xl">
                            {lead.name ? lead.name.charAt(0).toUpperCase() : "?"}
                        </div>
                        <div>
                            <h4 className="font-serif text-2xl text-[#0B0B0B]">
                                {lead.name || "Unknown"}
                            </h4>
                            <p className="text-sm text-[#5A5A5A] font-mono mt-1">
                                {lead.contact || "No contact"}
                            </p>
                        </div>
                    </div>

                    {/* Fields */}
                    <div className="grid grid-cols-2 gap-4">
                        {[
                            { label: "Region", value: lead.region },
                            { label: "Unit Type", value: lead.unit_type },
                            { label: "Purpose", value: lead.purpose },
                            { label: "Timeline", value: lead.timeline },
                            {
                                label: "Budget",
                                value:
                                    lead.budget_min || lead.budget_max
                                        ? `${fmtNum(lead.budget_min)} – ${fmtNum(lead.budget_max)}`
                                        : null,
                            },
                            { label: "Date", value: fmtDate(lead.timestamp) },
                        ].map((f, i) => (
                            <div key={i}>
                                <span className="text-[10px] font-bold tracking-[0.15em] uppercase text-[#5A5A5A]">
                                    {f.label}
                                </span>
                                <p className="text-sm text-[#0B0B0B] mt-1">{f.value || "—"}</p>
                            </div>
                        ))}
                    </div>

                    {/* Projects */}
                    {lead.projects.length > 0 && (
                        <div>
                            <span className="text-[10px] font-bold tracking-[0.15em] uppercase text-[#5A5A5A]">
                                Projects of Interest
                            </span>
                            <div className="flex flex-wrap gap-2 mt-2">
                                {lead.projects.map((p, i) => (
                                    <span
                                        key={i}
                                        className="px-3 py-1 bg-[#FAFAFA] border border-[#E9E9E9] rounded-full text-xs text-[#0B0B0B]"
                                    >
                                        {p}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Tags */}
                    {lead.tags.length > 0 && (
                        <div>
                            <span className="text-[10px] font-bold tracking-[0.15em] uppercase text-[#5A5A5A]">
                                Tags
                            </span>
                            <div className="flex flex-wrap gap-2 mt-2">
                                {lead.tags.map((t, i) => (
                                    <span
                                        key={i}
                                        className="px-2 py-0.5 bg-[#D22048]/5 border border-[#D22048]/10 rounded text-[10px] text-[#D22048]"
                                    >
                                        {t}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Summary */}
                    {lead.summary && (
                        <div>
                            <span className="text-[10px] font-bold tracking-[0.15em] uppercase text-[#5A5A5A]">
                                Summary
                            </span>
                            <p className="text-sm text-[#0B0B0B] mt-2 leading-relaxed bg-[#FAFAFA] p-4 rounded-xl border border-[#E9E9E9]">
                                {lead.summary}
                            </p>
                        </div>
                    )}

                    {/* Raw JSON */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-[10px] font-bold tracking-[0.15em] uppercase text-[#5A5A5A]">
                                Raw Data
                            </span>
                            <button
                                onClick={copyJson}
                                className="flex items-center gap-1 text-[10px] text-[#5A5A5A] hover:text-[#0B0B0B] transition-colors"
                            >
                                <Copy size={10} />
                                {copied ? "Copied" : "Copy JSON"}
                            </button>
                        </div>
                        <pre className="text-[11px] bg-[#0B0B0B] text-white/80 p-4 rounded-xl overflow-x-auto font-mono leading-relaxed max-h-64 overflow-y-auto">
                            {JSON.stringify(lead.raw, null, 2)}
                        </pre>
                    </div>
                </div>
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Main Dashboard Component
// ---------------------------------------------------------------------------
export default function Dashboard() {
    // State
    const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
    const [leads, setLeads] = useState<NormalizedLead[]>([]);
    const [sheets, setSheets] = useState<SheetInfo[]>([]);
    const [auditData, setAuditData] = useState<AuditData | null>(null);
    const [health, setHealth] = useState<HealthData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Leads table state
    const [search, setSearch] = useState("");
    const [regionFilter, setRegionFilter] = useState("All");
    const [sortField, setSortField] = useState<"timestamp" | "name">("timestamp");
    const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
    const [selectedLead, setSelectedLead] = useState<NormalizedLead | null>(null);

    // Sheets preview state
    const [previewSheet, setPreviewSheet] = useState<string | null>(null);
    const [previewData, setPreviewData] = useState<SheetPreview | null>(null);
    const [previewLoading, setPreviewLoading] = useState(false);

    // Range
    const [timeRange, setTimeRange] = useState("all");

    // Data sheet selector
    const [activeSheet, setActiveSheet] = useState("leads.csv");

    // --------------------------------------------------
    // Fetch data
    // --------------------------------------------------
    const fetchAll = async (sheet = activeSheet, range = timeRange) => {
        setLoading(true);
        setError(null);
        try {
            const [h, s, a, l, au] = await Promise.all([
                adminApi.health(),
                adminApi.sheets(),
                adminApi.analytics(sheet, range),
                adminApi.leads(sheet),
                adminApi.audit(),
            ]);
            setHealth(h);
            setSheets(s);
            setAnalytics(a);
            setLeads(l);
            setAuditData(au);
        } catch (e: any) {
            setError(e.message || "Failed to load data");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAll();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleRangeChange = (r: string) => {
        setTimeRange(r);
        fetchAll(activeSheet, r);
    };

    const handleSheetChange = (s: string) => {
        setActiveSheet(s);
        fetchAll(s, timeRange);
    };

    // --------------------------------------------------
    // Preview sheet
    // --------------------------------------------------
    const loadPreview = async (sheet: string) => {
        setPreviewSheet(sheet);
        setPreviewLoading(true);
        try {
            const data = await adminApi.preview(sheet, 50);
            setPreviewData(data);
        } catch {
            setPreviewData(null);
        } finally {
            setPreviewLoading(false);
        }
    };

    // --------------------------------------------------
    // Filtered + sorted leads
    // --------------------------------------------------
    const filteredLeads = useMemo(() => {
        let result = [...leads];

        // Search
        if (search) {
            const q = search.toLowerCase();
            result = result.filter(
                (l) =>
                    l.name?.toLowerCase().includes(q) ||
                    l.contact?.toLowerCase().includes(q) ||
                    l.projects?.some((p) => p.toLowerCase().includes(q)) ||
                    l.tags?.some((t) => t.toLowerCase().includes(q))
            );
        }

        // Region filter
        if (regionFilter !== "All") {
            result = result.filter(
                (l) => l.region?.toLowerCase() === regionFilter.toLowerCase()
            );
        }

        // Sort
        result.sort((a, b) => {
            const dir = sortDir === "asc" ? 1 : -1;
            if (sortField === "timestamp") {
                return (
                    dir *
                    (new Date(a.timestamp || 0).getTime() -
                        new Date(b.timestamp || 0).getTime())
                );
            }
            return dir * (a.name || "").localeCompare(b.name || "");
        });

        return result;
    }, [leads, search, regionFilter, sortField, sortDir]);

    // Unique regions for filter
    const regions = useMemo(() => {
        const set = new Set<string>();
        leads.forEach((l) => {
            if (l.region) set.add(l.region);
        });
        return ["All", ...Array.from(set).sort()];
    }, [leads]);

    // --------------------------------------------------
    // Error state
    // --------------------------------------------------
    if (error && !analytics) {
        return (
            <div className="min-h-screen bg-white flex items-center justify-center p-8">
                <div className="max-w-md text-center space-y-6">
                    <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto">
                        <AlertCircle size={24} className="text-[#D22048]" />
                    </div>
                    <h1 className="font-serif text-2xl text-[#0B0B0B]">
                        Connection Error
                    </h1>
                    <p className="text-sm text-[#5A5A5A] leading-relaxed">{error}</p>
                    {health && (
                        <div className="text-left bg-[#FAFAFA] border border-[#E9E9E9] rounded-xl p-4 text-xs font-mono space-y-1">
                            <p>Runtime: {health.resolved_runtime_dir}</p>
                            <p>
                                Leads Dir Exists: {health.leads_dir_exists ? "true" : "false"}
                            </p>
                            <p>Sheets: {health.available_sheets.join(", ") || "none"}</p>
                        </div>
                    )}
                    <button
                        onClick={() => fetchAll()}
                        className="px-6 py-3 bg-[#0B0B0B] text-white rounded-full text-xs font-bold tracking-widest uppercase hover:bg-[#D22048] transition-colors"
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    // --------------------------------------------------
    // Loading state
    // --------------------------------------------------
    if (loading && !analytics) {
        return (
            <div className="min-h-screen bg-white flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <Image
                        src="/brand/palmHills-BlockLogo.png"
                        alt="Palm Hills"
                        width={80}
                        height={80}
                        className="opacity-60"
                    />
                    <div className="w-48 h-1 bg-[#E9E9E9] rounded-full overflow-hidden">
                        <div className="h-full bg-[#D22048] rounded-full animate-pulse w-2/3" />
                    </div>
                    <p className="text-xs text-[#5A5A5A] tracking-widest uppercase">
                        Loading dashboard
                    </p>
                </div>
            </div>
        );
    }

    const kpis = analytics?.kpis;

    // --------------------------------------------------
    // Render
    // --------------------------------------------------
    return (
        <div className="min-h-screen bg-[#FAFAFA] text-[#0B0B0B] font-sans">
            {/* Header */}
            <header className="fixed top-0 w-full bg-white/95 backdrop-blur-md z-40 border-b border-[#E9E9E9] h-16 flex items-center justify-between px-6 md:px-10">
                <div className="flex items-center gap-4">
                    <Link href="/" className="flex items-center gap-3 group">
                        <Image
                            src="/brand/palmHills-BlockLogo.png"
                            alt="Palm Hills"
                            width={32}
                            height={32}
                            className="group-hover:opacity-80 transition-opacity"
                        />
                        <div className="hidden md:flex flex-col">
                            <span className="font-serif text-sm tracking-[0.15em] font-bold text-[#0B0B0B]">
                                PALM HILLS
                            </span>
                            <span className="text-[9px] uppercase tracking-[0.2em] text-[#D22048] font-medium">
                                PalmX Intelligence
                            </span>
                        </div>
                    </Link>
                </div>

                <div className="flex items-center gap-4">
                    {/* Sheet selector */}
                    <select
                        value={activeSheet}
                        onChange={(e) => handleSheetChange(e.target.value)}
                        className="text-xs bg-[#FAFAFA] border border-[#E9E9E9] rounded-lg px-3 py-2 outline-none focus:border-[#0B0B0B] transition-colors"
                    >
                        {sheets
                            .filter((s) => s.name.includes("lead"))
                            .map((s) => (
                                <option key={s.name} value={s.name}>
                                    {s.name}
                                </option>
                            ))}
                    </select>

                    {/* Range selector */}
                    <div className="flex bg-[#FAFAFA] border border-[#E9E9E9] rounded-lg p-0.5">
                        {["24h", "7d", "30d", "all"].map((r) => (
                            <button
                                key={r}
                                onClick={() => handleRangeChange(r)}
                                className={`px-3 py-1.5 rounded-md text-[10px] font-bold tracking-wider uppercase transition-all ${timeRange === r
                                        ? "bg-white text-[#0B0B0B] shadow-sm"
                                        : "text-[#5A5A5A] hover:text-[#0B0B0B]"
                                    }`}
                            >
                                {r}
                            </button>
                        ))}
                    </div>

                    <button
                        onClick={() => fetchAll()}
                        className="w-8 h-8 rounded-lg bg-[#FAFAFA] border border-[#E9E9E9] flex items-center justify-center text-[#5A5A5A] hover:text-[#0B0B0B] hover:border-[#0B0B0B] transition-colors"
                    >
                        <RefreshCw size={12} />
                    </button>

                    <Link
                        href="/"
                        className="hidden md:flex px-4 py-2 bg-[#0B0B0B] text-white rounded-full text-[10px] font-bold tracking-widest uppercase hover:bg-[#D22048] transition-colors"
                    >
                        Concierge
                    </Link>
                </div>
            </header>

            {/* Main */}
            <main className="pt-24 pb-16 px-6 md:px-10 max-w-[1440px] mx-auto space-y-10">
                {/* Page title */}
                <div>
                    <h1 className="font-serif text-3xl md:text-4xl text-[#0B0B0B]">
                        Lead Intelligence
                    </h1>
                    <p className="text-[#5A5A5A] font-light text-base mt-2">
                        Real-time concierge analytics and data visibility.
                        {kpis && (
                            <span className="text-[#D22048] ml-2 font-medium">
                                {kpis.total} total leads
                            </span>
                        )}
                    </p>
                </div>

                {/* KPI Strip */}
                {kpis && (
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                        <KpiCard
                            label="Total Leads"
                            value={fmtNum(kpis.total)}
                            icon={Users}
                            accent
                        />
                        <KpiCard
                            label="Last 24h"
                            value={fmtNum(kpis.last_24h)}
                            icon={TrendingUp}
                        />
                        <KpiCard
                            label="Unique Contacts"
                            value={fmtNum(kpis.unique_contacts)}
                            icon={Users}
                        />
                        <KpiCard
                            label="Top Project"
                            value={kpis.top_project}
                            icon={Building2}
                        />
                        <KpiCard
                            label="Top Region"
                            value={kpis.top_region}
                            icon={MapPin}
                        />
                        <KpiCard
                            label="Budget Median"
                            value={
                                kpis.budget_median ? `${fmtNum(kpis.budget_median)} EGP` : "—"
                            }
                            icon={DollarSign}
                        />
                    </div>
                )}

                {/* Charts */}
                {analytics && (
                    <>
                        <SectionHeader title="Analytics" icon={BarChart3} />
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            {/* Leads over time */}
                            <ChartCard title="Leads Over Time">
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={analytics.timeseries}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#E9E9E9" />
                                        <XAxis
                                            dataKey="bucket"
                                            tick={{ fontSize: 10, fill: "#5A5A5A" }}
                                            tickFormatter={(v) =>
                                                v.length > 10 ? v.slice(5, 10) : v
                                            }
                                        />
                                        <YAxis
                                            tick={{ fontSize: 10, fill: "#5A5A5A" }}
                                            allowDecimals={false}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                fontSize: 12,
                                                borderRadius: 12,
                                                border: "1px solid #E9E9E9",
                                            }}
                                        />
                                        <Area
                                            type="monotone"
                                            dataKey="count"
                                            stroke={ACCENT}
                                            fill={ACCENT}
                                            fillOpacity={0.08}
                                            strokeWidth={2}
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </ChartCard>

                            {/* By Project */}
                            <ChartCard title="Top Projects">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart
                                        data={analytics.breakdowns.by_project}
                                        layout="vertical"
                                    >
                                        <CartesianGrid
                                            strokeDasharray="3 3"
                                            stroke="#E9E9E9"
                                            horizontal={false}
                                        />
                                        <XAxis
                                            type="number"
                                            tick={{ fontSize: 10, fill: "#5A5A5A" }}
                                            allowDecimals={false}
                                        />
                                        <YAxis
                                            dataKey="label"
                                            type="category"
                                            tick={{ fontSize: 10, fill: "#5A5A5A" }}
                                            width={120}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                fontSize: 12,
                                                borderRadius: 12,
                                                border: "1px solid #E9E9E9",
                                            }}
                                        />
                                        <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                                            {analytics.breakdowns.by_project.map((_, i) => (
                                                <Cell
                                                    key={i}
                                                    fill={i === 0 ? ACCENT : CHART_COLORS[i % CHART_COLORS.length]}
                                                />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </ChartCard>

                            {/* By Region */}
                            <ChartCard title="By Region">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={analytics.breakdowns.by_region}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#E9E9E9" />
                                        <XAxis
                                            dataKey="label"
                                            tick={{ fontSize: 10, fill: "#5A5A5A" }}
                                        />
                                        <YAxis
                                            tick={{ fontSize: 10, fill: "#5A5A5A" }}
                                            allowDecimals={false}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                fontSize: 12,
                                                borderRadius: 12,
                                                border: "1px solid #E9E9E9",
                                            }}
                                        />
                                        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                            {analytics.breakdowns.by_region.map((_, i) => (
                                                <Cell
                                                    key={i}
                                                    fill={i === 0 ? ACCENT : CHART_COLORS[i % CHART_COLORS.length]}
                                                />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </ChartCard>

                            {/* Unit Type + Purpose + Timeline as pie/bar */}
                            <ChartCard title="Unit Type Distribution">
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={analytics.breakdowns.by_unit_type}
                                            dataKey="count"
                                            nameKey="label"
                                            cx="50%"
                                            cy="50%"
                                            outerRadius={90}
                                            innerRadius={50}
                                            strokeWidth={2}
                                            stroke="#fff"
                                        >
                                            {analytics.breakdowns.by_unit_type.map((_, i) => (
                                                <Cell key={i} fill={CHART_ACCENT[i % CHART_ACCENT.length]} />
                                            ))}
                                        </Pie>
                                        <Tooltip
                                            contentStyle={{
                                                fontSize: 12,
                                                borderRadius: 12,
                                                border: "1px solid #E9E9E9",
                                            }}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                            </ChartCard>

                            {/* Purpose */}
                            <ChartCard title="Purpose Distribution">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={analytics.breakdowns.by_purpose}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#E9E9E9" />
                                        <XAxis
                                            dataKey="label"
                                            tick={{ fontSize: 10, fill: "#5A5A5A" }}
                                        />
                                        <YAxis
                                            tick={{ fontSize: 10, fill: "#5A5A5A" }}
                                            allowDecimals={false}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                fontSize: 12,
                                                borderRadius: 12,
                                                border: "1px solid #E9E9E9",
                                            }}
                                        />
                                        <Bar dataKey="count" fill={ACCENT} radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </ChartCard>

                            {/* Timeline */}
                            <ChartCard title="Timeline Distribution">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={analytics.breakdowns.by_timeline}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#E9E9E9" />
                                        <XAxis
                                            dataKey="label"
                                            tick={{ fontSize: 10, fill: "#5A5A5A" }}
                                        />
                                        <YAxis
                                            tick={{ fontSize: 10, fill: "#5A5A5A" }}
                                            allowDecimals={false}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                fontSize: 12,
                                                borderRadius: 12,
                                                border: "1px solid #E9E9E9",
                                            }}
                                        />
                                        <Bar
                                            dataKey="count"
                                            fill="#0B0B0B"
                                            radius={[4, 4, 0, 0]}
                                        />
                                    </BarChart>
                                </ResponsiveContainer>
                            </ChartCard>
                        </div>
                    </>
                )}

                {/* Leads Table */}
                <div>
                    <SectionHeader title="Leads" icon={Table2} />

                    {/* Filters */}
                    <div className="flex flex-col md:flex-row gap-4 mb-4 items-start md:items-center">
                        <div className="relative flex-1 max-w-sm">
                            <Search
                                className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9A9A9A]"
                                size={14}
                            />
                            <input
                                type="text"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Search name, phone, project, tag..."
                                className="w-full pl-9 pr-4 py-2.5 bg-white border border-[#E9E9E9] rounded-xl text-xs outline-none focus:border-[#0B0B0B] transition-colors"
                            />
                        </div>
                        <div className="flex gap-1 bg-white border border-[#E9E9E9] rounded-lg p-0.5">
                            {regions.map((r) => (
                                <button
                                    key={r}
                                    onClick={() => setRegionFilter(r)}
                                    className={`px-3 py-1.5 rounded-md text-[10px] font-bold tracking-wider uppercase transition-all ${regionFilter === r
                                            ? "bg-[#FAFAFA] text-[#0B0B0B] shadow-sm"
                                            : "text-[#5A5A5A] hover:text-[#0B0B0B]"
                                        }`}
                                >
                                    {r}
                                </button>
                            ))}
                        </div>
                        <button
                            onClick={() => {
                                setSortField(sortField === "timestamp" ? "name" : "timestamp");
                                setSortDir((d) => (d === "asc" ? "desc" : "asc"));
                            }}
                            className="flex items-center gap-1 text-[10px] font-bold tracking-wider uppercase text-[#5A5A5A] hover:text-[#0B0B0B] transition-colors"
                        >
                            <ArrowUpDown size={12} />
                            {sortField} {sortDir}
                        </button>
                    </div>

                    {/* Table */}
                    <div className="bg-white border border-[#E9E9E9] rounded-2xl overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead className="bg-[#FAFAFA] text-[10px] uppercase tracking-wider text-[#5A5A5A] font-medium">
                                    <tr>
                                        <th className="px-5 py-3 font-medium">Name</th>
                                        <th className="px-5 py-3 font-medium">Contact</th>
                                        <th className="px-5 py-3 font-medium">Interest</th>
                                        <th className="px-5 py-3 font-medium">Budget</th>
                                        <th className="px-5 py-3 font-medium">Region</th>
                                        <th className="px-5 py-3 font-medium">Tags</th>
                                        <th className="px-5 py-3 font-medium text-right">Date</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[#E9E9E9]/50">
                                    {filteredLeads.slice(0, 100).map((lead, i) => (
                                        <tr
                                            key={i}
                                            onClick={() => setSelectedLead(lead)}
                                            className="hover:bg-[#FAFAFA] cursor-pointer transition-colors group"
                                        >
                                            <td className="px-5 py-3">
                                                <span className="text-sm font-medium text-[#0B0B0B]">
                                                    {lead.name || "—"}
                                                </span>
                                            </td>
                                            <td className="px-5 py-3">
                                                <span className="text-xs font-mono text-[#5A5A5A]">
                                                    {lead.contact || "—"}
                                                </span>
                                            </td>
                                            <td className="px-5 py-3">
                                                <span className="text-xs text-[#0B0B0B]">
                                                    {lead.projects?.slice(0, 2).join(", ") || "—"}
                                                </span>
                                                <div className="text-[10px] text-[#9A9A9A] mt-0.5">
                                                    {[lead.unit_type, lead.purpose]
                                                        .filter(Boolean)
                                                        .join(" · ")}
                                                </div>
                                            </td>
                                            <td className="px-5 py-3">
                                                <span className="text-xs text-[#5A5A5A]">
                                                    {lead.budget_min || lead.budget_max
                                                        ? `${fmtNum(lead.budget_min)}–${fmtNum(lead.budget_max)}`
                                                        : "—"}
                                                </span>
                                            </td>
                                            <td className="px-5 py-3">
                                                <span className="text-xs text-[#5A5A5A]">
                                                    {lead.region || "—"}
                                                </span>
                                            </td>
                                            <td className="px-5 py-3">
                                                <div className="flex flex-wrap gap-1">
                                                    {lead.tags?.slice(0, 3).map((t, j) => (
                                                        <span
                                                            key={j}
                                                            className="px-1.5 py-0.5 bg-[#FAFAFA] border border-[#E9E9E9] rounded text-[9px] text-[#5A5A5A]"
                                                        >
                                                            {t}
                                                        </span>
                                                    ))}
                                                </div>
                                            </td>
                                            <td className="px-5 py-3 text-right">
                                                <div className="text-[11px] text-[#5A5A5A]">
                                                    {fmtDate(lead.timestamp)}
                                                </div>
                                                <div className="text-[9px] text-[#9A9A9A] mt-0.5">
                                                    {fmtTime(lead.timestamp)}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        {filteredLeads.length === 0 && (
                            <div className="p-12 text-center text-[#9A9A9A] text-sm font-light">
                                No leads found matching your criteria.
                            </div>
                        )}
                        {filteredLeads.length > 100 && (
                            <div className="p-4 text-center text-[10px] text-[#9A9A9A] tracking-wider uppercase bg-[#FAFAFA] border-t border-[#E9E9E9]">
                                Showing 100 of {filteredLeads.length} leads
                            </div>
                        )}
                    </div>
                </div>

                {/* Sheets Browser */}
                <div>
                    <SectionHeader title="Runtime Sheets" id="sheets" icon={FileSpreadsheet} />
                    {sheets.length === 0 ? (
                        <div className="bg-white border border-[#E9E9E9] rounded-2xl p-8 text-center">
                            <FileSpreadsheet size={32} className="mx-auto text-[#9A9A9A] mb-4" />
                            <p className="text-sm text-[#5A5A5A]">No sheets found.</p>
                            <p className="text-xs text-[#9A9A9A] mt-2">
                                Place .csv or .xlsx files under{" "}
                                <code className="bg-[#FAFAFA] px-2 py-0.5 rounded text-[10px]">
                                    runtime/leads/
                                </code>
                            </p>
                            {health && (
                                <p className="text-[10px] text-[#9A9A9A] mt-2 font-mono">
                                    Runtime dir: {health.resolved_runtime_dir}
                                </p>
                            )}
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {sheets.map((s) => (
                                <div
                                    key={s.name}
                                    className="bg-white border border-[#E9E9E9] rounded-2xl overflow-hidden"
                                >
                                    <div className="flex items-center justify-between p-5">
                                        <div className="flex items-center gap-4">
                                            <div className="w-10 h-10 rounded-xl bg-[#FAFAFA] border border-[#E9E9E9] flex items-center justify-center">
                                                <FileSpreadsheet size={16} className="text-[#5A5A5A]" />
                                            </div>
                                            <div>
                                                <h4 className="text-sm font-medium text-[#0B0B0B]">
                                                    {s.name}
                                                </h4>
                                                <p className="text-[10px] text-[#9A9A9A] mt-0.5">
                                                    {s.rows >= 0 ? `${s.rows} rows` : "error"} ·{" "}
                                                    {s.cols >= 0 ? `${s.cols} cols` : ""} ·{" "}
                                                    {s.type.toUpperCase()} · Modified{" "}
                                                    {fmtDate(s.modified_at)}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() =>
                                                    previewSheet === s.name
                                                        ? setPreviewSheet(null)
                                                        : loadPreview(s.name)
                                                }
                                                className="flex items-center gap-1 px-3 py-1.5 text-[10px] font-bold tracking-wider uppercase bg-[#FAFAFA] border border-[#E9E9E9] rounded-lg text-[#5A5A5A] hover:text-[#0B0B0B] hover:border-[#0B0B0B] transition-colors"
                                            >
                                                <Eye size={10} />
                                                {previewSheet === s.name ? "Close" : "Preview"}
                                            </button>
                                            <a
                                                href={adminApi.downloadUrl(s.name, "original")}
                                                className="flex items-center gap-1 px-3 py-1.5 text-[10px] font-bold tracking-wider uppercase bg-[#FAFAFA] border border-[#E9E9E9] rounded-lg text-[#5A5A5A] hover:text-[#0B0B0B] hover:border-[#0B0B0B] transition-colors"
                                            >
                                                <Download size={10} />
                                                Original
                                            </a>
                                            <a
                                                href={adminApi.downloadUrl(s.name, "xlsx")}
                                                className="flex items-center gap-1 px-3 py-1.5 text-[10px] font-bold tracking-wider uppercase bg-[#0B0B0B] text-white rounded-lg hover:bg-[#D22048] transition-colors"
                                            >
                                                <Download size={10} />
                                                XLSX
                                            </a>
                                        </div>
                                    </div>

                                    {/* Preview table */}
                                    {previewSheet === s.name && (
                                        <div className="border-t border-[#E9E9E9] max-h-96 overflow-auto">
                                            {previewLoading ? (
                                                <div className="p-8 text-center text-xs text-[#9A9A9A]">
                                                    Loading preview...
                                                </div>
                                            ) : previewData ? (
                                                <table className="w-full text-left text-xs">
                                                    <thead className="bg-[#FAFAFA] sticky top-0">
                                                        <tr>
                                                            {previewData.columns.map((c) => (
                                                                <th
                                                                    key={c}
                                                                    className="px-4 py-2 text-[9px] font-bold tracking-wider uppercase text-[#5A5A5A] whitespace-nowrap"
                                                                >
                                                                    {c}
                                                                </th>
                                                            ))}
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-[#E9E9E9]/50">
                                                        {previewData.rows.map((row, i) => (
                                                            <tr key={i} className="hover:bg-[#FAFAFA]/50">
                                                                {previewData!.columns.map((c) => (
                                                                    <td
                                                                        key={c}
                                                                        className="px-4 py-2 text-[11px] text-[#5A5A5A] max-w-[200px] truncate whitespace-nowrap"
                                                                    >
                                                                        {row[c] || ""}
                                                                    </td>
                                                                ))}
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            ) : (
                                                <div className="p-8 text-center text-xs text-[#9A9A9A]">
                                                    Failed to load preview.
                                                </div>
                                            )}
                                            {previewData && (
                                                <div className="p-3 text-center text-[10px] text-[#9A9A9A] bg-[#FAFAFA] border-t border-[#E9E9E9]">
                                                    Showing {previewData.showing} of{" "}
                                                    {previewData.total_rows} rows
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Audit Section */}
                <div>
                    <SectionHeader title="Retrieval Quality" id="audit" icon={Activity} />
                    {!auditData || !auditData.available ? (
                        <div className="bg-white border border-[#E9E9E9] rounded-2xl p-8 text-center">
                            <Activity size={32} className="mx-auto text-[#9A9A9A] mb-4" />
                            <p className="text-sm text-[#5A5A5A]">
                                {auditData?.message || "No audit dataset found."}
                            </p>
                            <p className="text-xs text-[#9A9A9A] mt-2">
                                Place an{" "}
                                <code className="bg-[#FAFAFA] px-2 py-0.5 rounded text-[10px]">
                                    audit.csv
                                </code>{" "}
                                in runtime/leads/ to enable retrieval quality analytics.
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            <KpiCard
                                label="Total Queries"
                                value={fmtNum(auditData.total_queries || 0)}
                                icon={Activity}
                            />
                            <KpiCard
                                label="Empty Retrieval"
                                value={`${((auditData.empty_retrieval_rate || 0) * 100).toFixed(1)}%`}
                                icon={AlertCircle}
                                accent={
                                    (auditData.empty_retrieval_rate || 0) > 0.2
                                }
                            />
                            <KpiCard
                                label="Top Retrieved"
                                value={
                                    auditData.top_retrieved_projects?.[0]?.project || "—"
                                }
                                icon={Building2}
                            />

                            {/* Score histogram */}
                            {auditData.score_histogram &&
                                auditData.score_histogram.length > 0 && (
                                    <div className="md:col-span-2 lg:col-span-3">
                                        <ChartCard title="Similarity Score Distribution">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <BarChart data={auditData.score_histogram}>
                                                    <CartesianGrid
                                                        strokeDasharray="3 3"
                                                        stroke="#E9E9E9"
                                                    />
                                                    <XAxis
                                                        dataKey="range"
                                                        tick={{ fontSize: 10, fill: "#5A5A5A" }}
                                                    />
                                                    <YAxis
                                                        tick={{ fontSize: 10, fill: "#5A5A5A" }}
                                                        allowDecimals={false}
                                                    />
                                                    <Tooltip
                                                        contentStyle={{
                                                            fontSize: 12,
                                                            borderRadius: 12,
                                                            border: "1px solid #E9E9E9",
                                                        }}
                                                    />
                                                    <Bar
                                                        dataKey="count"
                                                        fill="#0B0B0B"
                                                        radius={[4, 4, 0, 0]}
                                                    />
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </ChartCard>
                                    </div>
                                )}
                        </div>
                    )}
                </div>

                {/* Executive Narrative */}
                <div>
                    <SectionHeader title="Executive Summary" icon={FileText} />
                    <div className="bg-white border border-[#E9E9E9] rounded-2xl p-8 space-y-8">
                        <div>
                            <h3 className="font-serif text-xl text-[#0B0B0B] mb-4">
                                What This Proves
                            </h3>
                            <ul className="space-y-3">
                                {[
                                    "AI concierge captures qualified leads through natural conversation, not forms — improving conversion quality.",
                                    "Every interaction is enriched with project interest, budget signals, timeline, and purchase intent.",
                                    "Lead data is structured and export-ready for CRM, call center, or executive reporting workflows.",
                                    "The system serves verified information only, eliminating misinformation risk from sales teams.",
                                    "Real-time dashboard provides instant visibility into demand patterns across the entire portfolio.",
                                    "Retrieval quality tracking ensures the AI's accuracy is measurable and improvable.",
                                    "24/7 availability captures leads outside business hours — a segment typically lost.",
                                ].map((item, i) => (
                                    <li key={i} className="flex items-start gap-3">
                                        <span className="w-1.5 h-1.5 rounded-full bg-[#D22048] mt-2 flex-shrink-0" />
                                        <span className="text-sm text-[#5A5A5A] leading-relaxed">
                                            {item}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        <div className="border-t border-[#E9E9E9] pt-8">
                            <h3 className="font-serif text-xl text-[#0B0B0B] mb-4">
                                Next Expansion Scope
                            </h3>
                            <ul className="space-y-3">
                                {[
                                    "Phase 1: CRM integration (Salesforce/HubSpot) for real-time lead push and lifecycle tracking.",
                                    "Phase 2: Call center workflow — warm transfer with pre-qualified lead context to sales consultants.",
                                    "Phase 3: Multilingual support (Arabic, French) with culturally-adapted conversation flows.",
                                    "Phase 4: Live pricing and availability sync from internal inventory systems.",
                                    "Phase 5: Role-based admin access (RBAC) with team-level analytics and audit trails.",
                                    "Phase 6: Voice assistant integration for phone-based and in-app concierge experiences.",
                                    "Phase 7: Predictive analytics — demand forecasting, price sensitivity modeling, and buyer scoring.",
                                ].map((item, i) => (
                                    <li key={i} className="flex items-start gap-3">
                                        <span className="w-1.5 h-1.5 rounded-full bg-[#0B0B0B] mt-2 flex-shrink-0" />
                                        <span className="text-sm text-[#5A5A5A] leading-relaxed">
                                            {item}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            </main>

            {/* Footer */}
            <footer className="border-t border-[#E9E9E9] bg-white px-6 md:px-10 py-6">
                <div className="max-w-[1440px] mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
                    <p className="text-[10px] text-[#9A9A9A] tracking-widest uppercase">
                        © {new Date().getFullYear()} Palm Hills Developments. All rights
                        reserved.
                    </p>
                    <div className="flex items-center gap-4 text-[10px] text-[#9A9A9A] tracking-wider uppercase">
                        <Link href="/" className="hover:text-[#0B0B0B] transition-colors">
                            Concierge
                        </Link>
                        <span className="w-px h-3 bg-[#E9E9E9]" />
                        <a
                            href="https://cloudgate.ae/"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-[#0B0B0B] transition-colors"
                        >
                            Developed by CloudGate
                        </a>
                    </div>
                </div>
            </footer>

            {/* Lead Detail Drawer */}
            {selectedLead && (
                <LeadDetailDrawer
                    lead={selectedLead}
                    onClose={() => setSelectedLead(null)}
                />
            )}
        </div>
    );
}
