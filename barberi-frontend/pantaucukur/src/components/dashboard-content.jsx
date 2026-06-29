"use client";

import { ChairStatusGrid } from "./chair-status-grid";
import { cn } from "./lib/utils";
import { Armchair, TrendingUp, Users, DollarSign, Timer, User2 } from "lucide-react";
import { useState } from "react";
import { SessionHistoryContainer } from "./session-history-container";

// --- Sub-Component: SkeletonBar ---
function SkeletonBar({ className }) {
  return (
    <div className={cn("rounded-md bg-muted animate-shimmer", className)} />
  );
}

// --- Sub-Component: StatCard ---
function StatCard({ icon: Icon, label, value, trend, isLoading = false }) {
  return (
    <div className={cn(
      "relative flex flex-col gap-2 p-4 rounded-2xl bg-card transition-all duration-300",
      "border-t-1 border-t-white/20 border-x-white/5 border-b-white/5 shadow-xl overflow-hidden",
      "bg-gradient-to-br from-white/[0.03] to-transparent"
    )}>
      <div className="flex items-center justify-between relative z-10">
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="p-1.5 rounded-lg bg-white/5 border border-white/10">
            {Icon && <Icon className="w-3.5 h-3.5 text-white/70" />}
          </div>
          <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">
            {label}
          </span>
        </div>
        {!isLoading && trend && (
          <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded-md">
            {trend}
          </span>
        )}
      </div>

      <div className="mt-1 relative z-10">
        {isLoading ? (
          <SkeletonBar className="h-8 w-28 opacity-20" />
        ) : (
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-black tracking-tight text-foreground">
              {value}
            </span>
            {label.toLowerCase().includes('revenue') && 
              <span className="text-xs text-muted-foreground font-medium">K</span>
            }
          </div>
        )}
      </div>
      <div className="absolute -bottom-4 -right-4 w-12 h-12 bg-white/5 blur-2xl rounded-full" />
    </div>
  );
}



// --- Main Component: DashboardContent ---
export function DashboardContent() {
  const [loading] = useState(false);

  return (
    <main className="flex-1 overflow-y-auto bg-background">
      <div className="px-4 py-6 space-y-6">
        
        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4">
          <StatCard 
            icon={Users} 
            label="Customers Today" 
            value="24" 
            trend="+12%"
            isLoading={loading} 
          />
          <StatCard 
            icon={DollarSign} 
            label="Daily Revenue" 
            value="1.2" 
            trend="+5%"
            isLoading={loading} 
          />
        </div>

        <ChairStatusGrid />

        <SessionHistoryContainer />  

        <div className="h-8" /> {/* Spacer extra agar tidak tertutup navbar bawah */}
      </div>
    </main>
  );
}