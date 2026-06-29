// src/pages/SessionHistory.jsx
"use client";

import React, { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { 
  ArrowLeft, 
  Search, 
  Calendar, 
  Sparkles 
} from "lucide-react";

// Import Custom Modules
import { cn, normalizeSession } from "../components/lib/utils";
import { sessionService } from "../components/services/api";
import { SessionList } from "../components/ui/session-list";

// Import UI Components (Shadcn UI style)
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";

export function SessionHistory({ chairId }) {
  // --- STATE MANAGEMENT ---
  const [searchQuery, setSearchQuery] = useState("");
  const [dateFilter, setDateFilter] = useState("today");
  const [loading, setLoading] = useState(true);
  const [sessions, setSessions] = useState({
    summary: { total_valid: 0, total_invalid: 0 },
    valid_list: [],
    invalid_list: []
  });

  // --- DATA FETCHING (POLLING 5s) ---
  useEffect(() => {
  // 1. Ambil data awal
    loadData();

    // 2. Gunakan jalur telepon (WebSocket) yang sama
    const socket = new WebSocket('ws://127.0.0.1:8000/ws/sessions/');

    socket.onmessage = (event) => {
      const newData = JSON.parse(event.data);
      // Update state hanya saat ada kabar baru dari AI Engine
      setSessions(newData.updated_summary || newData);
    };

    return () => socket.close(); // Ingat selalu matikan asistennya
  }, []);

  // --- LOGIKA FILTERING (REAKTIF & OPTIMAL) ---
  const { searchValid, searchAnomalies } = useMemo(() => {
    // Normalisasi data API ke format UI
    const realValid = sessions.valid_list.map(normalizeSession);
    const realAnomalies = sessions.invalid_list.map(normalizeSession);

    const applyFilters = (s) => {
      const matchesSearch = s.chairName.toLowerCase().includes(searchQuery.toLowerCase());
      // Handle jika chairId datang dari props (untuk filter per kursi)
      const matchesChair = chairId ? Number(s.chairId) === Number(chairId) : true;
      return matchesSearch && matchesChair;
    };

    return {
      searchValid: realValid.filter(applyFilters),
      searchAnomalies: realAnomalies.filter(applyFilters)
    };
  }, [sessions, searchQuery, chairId]);

  // --- RENDER LOADING STATE ---
  if (loading && sessions.valid_list.length === 0) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-2">
          <Sparkles className="w-8 h-8 text-primary animate-pulse" />
          <p className="text-sm text-muted-foreground animate-pulse font-medium">
            Syncing AI Engine...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      {/* HEADER SECTION */}
      <header className="sticky top-0 z-10 flex items-center gap-3 px-4 py-3 bg-background/95 backdrop-blur-md border-b border-border safe-top">
        <Link to="/">
          <button
            className="flex items-center justify-center w-10 h-10 -ml-1 rounded-xl hover:bg-secondary active:scale-95 transition-all"
            aria-label="Back to Dashboard"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
        </Link>
        <div>
          <h1 className="text-lg font-bold tracking-tight">Riwayat Sesi</h1>
          <p className="text-[10px] text-muted-foreground uppercase font-semibold tracking-widest">
            {chairId ? `Kursi 0${chairId}` : "Semua Kursi"} • Laba AI Engine
          </p>
        </div>
      </header>

      {/* FILTER SECTION */}
      <div className="flex flex-col gap-3 px-4 py-4 bg-background border-b border-border shadow-sm">
        {/* Search Input */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Cari nomor kursi..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-11 rounded-2xl bg-secondary/50 border-transparent focus:ring-1 focus:ring-primary transition-all"
          />
        </div>

        {/* Date Filter */}
        <Select value={dateFilter} onValueChange={setDateFilter}>
          <SelectTrigger className="h-10 rounded-2xl bg-secondary/50 border-transparent font-medium">
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="w-4 h-4 text-muted-foreground" />
              <SelectValue placeholder="Pilih Tanggal" />
            </div>
          </SelectTrigger>
          <SelectContent className="rounded-xl border-border bg-popover/95 backdrop-blur-lg">
            <SelectItem value="today">Hari Ini</SelectItem>
            <SelectItem value="yesterday">Kemarin</SelectItem>
            <SelectItem value="week">Minggu Ini</SelectItem>
            <SelectItem value="month">Bulan Ini</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* REUSABLE LIST SECTION */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden">
        <SessionList 
          validSessions={searchValid} 
          anomalySessions={searchAnomalies} 
        />
      </div>
    </div>
  );
}

export default SessionHistory;