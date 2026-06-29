// src/pages/Analytics.jsx
"use client";

import { BarberLeaderboard } from "../components/barber-leaderboard";
import { BottomNavigation } from "../components/bottom-navigation";
import { MobileHeader } from "../components/mobile-header";
import { TrafficAnalyticsChart } from "../components/traffic-analytics-chart";

export default function AnalyticsPage() {
  return (
    // min-h-screen memastikan background menutupi seluruh layar
    // flex-col dengan gap agar antar komponen punya jarak konsisten
    <div className="flex flex-col min-h-screen bg-background text-foreground">
      
      {/* 1. Header tetap di atas */}
      <MobileHeader />

      {/* 2. Main Content Area */}
      {/* pb-24 memberikan ruang agar konten bawah tidak tertutup BottomNavigation */}
      <main className="flex-1 px-4 pt-4 pb-24 space-y-6 overflow-y-auto">
        
        {/* Section: Traffic */}
        <section className="space-y-3">
            
          <div className="flex flex-col">
            <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground ml-1">
              Traffic Insight
            </h2>
          </div>
          <div>
            <TrafficAnalyticsChart />
          </div>
        </section>

        {/* Section: Leaderboard */}
        <section className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground ml-1">
            Barber Performance
          </h2>
          <div className=" rounded-3xl overflow-hidden">
            <BarberLeaderboard />
          </div>
        </section>

      </main>

      {/* 3. Navigation tetap di bawah (Fixed melalui komponennya) */}
      <BottomNavigation />
    </div>
  );
}