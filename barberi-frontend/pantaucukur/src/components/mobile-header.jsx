

import { Bell } from "lucide-react";
import { useState } from "react";

export function MobileHeader() {
  const [hasNotifications] = useState(true);

  return (
    <header className="sticky top-0 z-50 safe-top bg-background/95 backdrop-blur-md border-b border-border">
      <div className="flex items-center justify-between px-4 h-14">
        {/* Brand */}
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold tracking-tight text-foreground">
            PantauCukur
          </span>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          {/* Live Indicator */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-live/10 border border-live/20">
            <span className="relative flex h-2 w-2">
              <span className="animate-pulse-live absolute inline-flex h-full w-full rounded-full bg-live opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-live" />
            </span>
            <span className="text-xs font-semibold text-live uppercase tracking-wider">
              Live
            </span>
          </div>

          {/* Notification Bell */}
          <button
            className="relative flex items-center justify-center w-11 h-11 rounded-xl bg-secondary hover:bg-secondary/80 transition-colors"
            aria-label="Notifications"
          >
            <Bell className="w-5 h-5 text-foreground" />
            {hasNotifications && (
              <span className="absolute top-2 right-2 flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-destructive opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-destructive" />
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
