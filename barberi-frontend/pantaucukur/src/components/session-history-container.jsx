// src/components/containers/SessionHistoryContainer.jsx
"use client";

import React, { useState, useEffect, useMemo } from "react";
import { Sparkles } from "lucide-react";
import { normalizeSession } from "../components/lib/utils";
import { sessionService } from "../components/services/api";
import { SessionList } from "./ui/session-list";

export function SessionHistoryContainer({ chairId = null, limit = null }) {
  const [sessions, setSessions] = useState({ valid_list: [], invalid_list: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Ambil data awal sekali saja (Initial Load)
    const loadInitialData = async () => {
      try {
        const result = await sessionService.getSummary();
        setSessions(result);
        setLoading(false);
      } catch (err) {
        setLoading(false);
      }
    };
    loadInitialData();

    // 2. Setup Jalur "Plong" WebSocket
    const socket = new WebSocket('ws://127.0.0.1:8000/ws/test/');

    socket.onmessage = (event) => {
      const response = JSON.parse(event.data);
      console.log("Kabar baru dari AI Engine!", response);
      
      // CEK STRUKTUR DATA
      // Jika ini INITIAL_CONNECTION atau STATUS_UPDATE
      const newData = response.updated_summary || response.data || response;

      if (newData.valid_list && newData.invalid_list) {
        setSessions(newData); // Templok langsung jika formatnya sudah summary lengkap
      }
    };

    socket.onclose = () => {
      console.warn("Jalur WebSocket putus. Server mungkin lagi restart.");
    };

    // 3. CLEANUP (Sangat Penting!)
    // Supaya pas pindah halaman, koneksinya diputus dan nggak numpuk di log server.
    return () => socket.close();
  }, []);

  const { filteredValid, filteredAnomalies } = useMemo(() => {
    const filterFn = (s) => (chairId ? Number(s.chair) === Number(chairId) : true);
    
    let valid = sessions.valid_list.filter(filterFn).map(normalizeSession);
    let anomalies = sessions.invalid_list.filter(filterFn).map(normalizeSession);

    // Jika ingin membatasi jumlah list (misal hanya tampil 5 terbaru di Monitoring)
    if (limit) {
      valid = valid.slice(0, limit);
      anomalies = anomalies.slice(0, limit);
    }

    return { filteredValid: valid, filteredAnomalies: anomalies };
  }, [sessions, chairId, limit]);

  if (loading && sessions.valid_list.length === 0) {
    return (
      <div className="flex p-12 items-center justify-center opacity-50">
        <Sparkles className="w-5 h-5 animate-pulse mr-2" />
        <span className="text-sm">Syncing AI Data...</span>
      </div>
    );
  }

  return (
    <SessionList 
      validSessions={filteredValid} 
      anomalySessions={filteredAnomalies} 
    />
  );
}