"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

interface AppState {
    systemReady: boolean;
    bootProgress: number;
    dashboardData: {
        analytics: any;
        leads: any[];
        sheets: any[];
        auditData: any;
        health: any;
    } | null;
    dashboardLoading: boolean;
    lastFetchTime: number | null;
}

interface AppContextType extends AppState {
    setSystemReady: (ready: boolean) => void;
    setBootProgress: (progress: number | ((prev: number) => number)) => void;
    setDashboardData: (data: AppState["dashboardData"]) => void;
    setDashboardLoading: (loading: boolean) => void;
    updateLastFetchTime: () => void;
    shouldRefetch: () => boolean;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

export function AppProvider({ children }: { children: ReactNode }) {
    const [systemReady, setSystemReady] = useState(false);
    const [bootProgressState, setBootProgressState] = useState(0);
    
    const setBootProgress = (progress: number | ((prev: number) => number)) => {
        if (typeof progress === 'function') {
            setBootProgressState(progress);
        } else {
            setBootProgressState(progress);
        }
    };
    const [dashboardData, setDashboardData] = useState<AppState["dashboardData"]>(null);
    const [dashboardLoading, setDashboardLoading] = useState(false);
    const [lastFetchTime, setLastFetchTime] = useState<number | null>(null);

    const updateLastFetchTime = () => {
        setLastFetchTime(Date.now());
    };

    const shouldRefetch = () => {
        if (!lastFetchTime) return true;
        return Date.now() - lastFetchTime > CACHE_DURATION;
    };

    // Persist systemReady to localStorage
    useEffect(() => {
        const stored = localStorage.getItem("palmx_system_ready");
        if (stored === "true") {
            setSystemReady(true);
            setBootProgress(100);
        }
    }, []);

    useEffect(() => {
        if (systemReady) {
            localStorage.setItem("palmx_system_ready", "true");
        }
    }, [systemReady]);

    return (
        <AppContext.Provider
            value={{
                systemReady,
                bootProgress: bootProgressState,
                dashboardData,
                dashboardLoading,
                lastFetchTime,
                setSystemReady,
                setBootProgress,
                setDashboardData,
                setDashboardLoading,
                updateLastFetchTime,
                shouldRefetch,
            }}
        >
            {children}
        </AppContext.Provider>
    );
}

export function useApp() {
    const context = useContext(AppContext);
    if (context === undefined) {
        throw new Error("useApp must be used within an AppProvider");
    }
    return context;
}

