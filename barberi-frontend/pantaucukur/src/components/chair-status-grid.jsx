"use client";

import { Link } from "react-router-dom";
import { cn } from "./lib/utils";
import { Scissors, Armchair } from "lucide-react";
import { useState, useEffect } from "react";

function formatTime(minutes) {
  const mins = Math.floor(minutes);
  const secs = Math.floor((minutes % 1) * 60);
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

function ChairCard({ chair }) {
  const [elapsed, setElapsed] = useState(0);
  const isOccupied = chair.isOccupied; 

  useEffect(() => {
    let interval;
    if (chair.isOccupied && chair.startTime) {
      // Update setiap detik agar timer jalan
      interval = setInterval(() => {
        const diff = (new Date() - new Date(chair.startTime)) / 1000 / 60;
        setElapsed(diff);
      }, 1000);
    } else {
      setElapsed(0);
    }
    return () => clearInterval(interval);
  }, [chair.isOccupied, chair.startTime]);

  return (
    <div
      className={cn(
        "relative flex flex-col gap-3 p-5 rounded-2xl border transition-all duration-200 active:scale-[0.98]",
        "h-[180px] w-full",
        isOccupied
          ? "bg-[var(--chair-occupied)] border-2 border-[var(--chair-occupied-border)] active-shimmer"
          : "bg-[var(--chair-vacant)] border-[var(--chair-vacant-border)]"
      )}
    >
      {/* Container Konten (di atas lapisan kilauan) */}
      <div className="relative z-10 flex flex-col h-full">
        
        {/* Bagian Atas: Icon & Nama */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-secondary/30 shrink-0">
            {isOccupied && (
              <span className="absolute inset-0 rounded-xl bg-[var(--chair-occupied-border)] animate-ping opacity-20" />
            )}
            {isOccupied ? (
              <Scissors className="w-5 h-5 text-[var(--chair-occupied-text)]" />
            ) : (
              <Armchair className="w-5 h-5 text-[var(--chair-vacant-text)]" />
            )}
          </div>
          <span className="text-sm font-bold text-foreground truncate">
            {chair.name}
          </span>
        </div>

        {/* Bagian Bawah: Timer/Status */}
        <div className="flex flex-col flex-1 justify-end">
          {isOccupied ? (
            <div className="space-y-2">
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-mono font-bold text-[var(--chair-occupied-text)]">
                  {formatTime(elapsed)}
                </span>
                <span className="text-[10px] text-muted-foreground uppercase">min</span>
              </div>
              
              {/* Progress Bar */}
              <div className="w-full h-1.5 rounded-full bg-secondary/50 overflow-hidden">
                <div
                  className="h-full rounded-full bg-[var(--chair-occupied-text)] transition-all duration-500"
                  style={{ width: `${chair.progress || 0}%` }}
                />
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <span className="text-2xl font-mono font-bold text-[var(--chair-vacant-text)] opacity-30">
                --:--
              </span>
              <div className="flex">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-[var(--chair-vacant-border)]/20 text-[var(--chair-vacant-text)] border border-[var(--chair-vacant-border)]/30">
                  Tersedia
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
export function ChairStatusGrid() {
  // State awal (bisa kamu sesuaikan jumlah kursinya)
  const [chairs, setChairs] = useState([
    { id: 1, name: "Kursi 01", isOccupied: false, startTime: null },
    { id: 2, name: "Kursi 02", isOccupied: false, startTime: null },
    { id: 3, name: "Kursi 03", isOccupied: false, startTime: null },
    { id: 4, name: "Kursi 04", isOccupied: false, startTime: null },
  ]);
  

  useEffect(() => {
    const socket = new WebSocket('ws://127.0.0.1:8000/ws/test/');

    socket.onmessage = (event) => {
      const response = JSON.parse(event.data);
      
      // Jika tipe pesan adalah STATUS_UPDATE dari Django views
      if (response.type === 'STATUS_UPDATE') {
        setChairs(prevChairs => prevChairs.map(chair => {
          if (chair.id === response.chair_id) {
            return {
              ...chair,
              isOccupied: response.is_occupied,
              // Simpan waktu mulai untuk hitung elapsed time di UI
              startTime: response.is_occupied ? new Date() : null 
            };
          }
          return chair;
        }));
      }
    };

    return () => socket.close();
  }, []);

  return (
    <div className="rounded-2xl bg-card border-t-1 border-white/10 shadow-sm overflow-hidden">
      {/* Section Header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-3">
        <div className="flex items-center gap-2">
          <Armchair className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">
            Chair Status
          </span>
        </div>
        <span className="text-xs text-muted-foreground">Real-time</span>
      </div>

      {/* Horizontal Scrollable Chair Cards */}
      <div
        className={cn(
          "flex gap-3 px-4 pb-4 overflow-x-auto",
          "snap-x snap-mandatory scroll-smooth",
          /* Hide scrollbar but keep functionality */
          "[&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]"
        )}
      >
        {chairs.map((chair) => (
          <Link to={'/session-history'} key={chair.id} className="snap-start shrink-0 w-[75%] min-w-[240px] max-w-[280px]">
            <ChairCard chair={chair} />
          </Link>
        ))}
        {/* Spacer for peek effect on last card */}
        <div className="shrink-0 w-4" aria-hidden="true" />
      </div>
    </div>
  );
}
