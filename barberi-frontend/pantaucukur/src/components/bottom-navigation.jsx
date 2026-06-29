"use client";

import { Home, BarChart3, Clock, Cog, Moon, Sun, User, LogOut } from "lucide-react";
import { useTheme } from "next-themes";
import { Link, useLocation } from "react-router-dom"; // Tambahkan ini
import { cn } from "./lib/utils"; 
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "./ui/sheet";
import { Switch } from "./ui/switch";

// Sesuaikan 'path' dengan route yang kamu daftarkan di App.jsx
const navItems = [
  { id: "monitoring", label: "Monitoring", icon: Home, path: "/" },
  { id: "analytics", label: "Analytics", icon: BarChart3, path: "/analytic-page" },
  { id: "history", label: "History", icon: Clock, path: "/history" },
];

function SettingsSheet() {
  const { theme, setTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <Sheet>
      <SheetTrigger asChild>
        <button
          className={cn(
            "flex flex-col items-center justify-center gap-1 min-w-[72px] h-12 rounded-xl transition-all duration-200",
            "text-muted-foreground hover:text-foreground active:scale-90"
          )}
          aria-label="Settings"
        >
          <div className="flex items-center justify-center w-11 h-7 rounded-lg transition-colors">
            <Cog className="w-5 h-5" strokeWidth={2} />
          </div>
          <span className="text-[10px] font-medium tracking-tighter uppercase font-bold">Settings</span>
        </button>
      </SheetTrigger>
      
      <SheetContent side="bottom" className="rounded-t-3xl pb-8 safe-bottom border-t-2 border-t-white/10 bg-background/95 backdrop-blur-xl">
        <SheetHeader className="pb-4">
          <SheetTitle className="text-left text-lg font-bold">Control Center</SheetTitle>
        </SheetHeader>

        <div className="flex flex-col gap-2 px-2">
          {/* Theme Toggle */}
          <div className="flex items-center justify-between p-4 rounded-2xl bg-secondary/30 border border-white/5">
            <div className="flex items-center gap-3">
              {isDark ? (
                <Moon className="w-5 h-5 text-orange-400" />
              ) : (
                <Sun className="w-5 h-5 text-amber-500" />
              )}
              <div className="flex flex-col">
                <span className="text-sm font-medium">Dark Mode</span>
                <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">
                  {isDark ? "Midnight Sun Enabled" : "High Contrast Light"}
                </span>
              </div>
            </div>
            <Switch
              checked={isDark}
              onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")}
            />
          </div>

          {/* Profile Settings */}
          <button className="flex items-center gap-3 p-4 rounded-2xl bg-secondary/30 border border-white/5 text-left transition-all active:scale-[0.98]">
            <User className="w-5 h-5 text-muted-foreground" />
            <div className="flex flex-col">
              <span className="text-sm font-medium">Laba AI Account</span>
              <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">Manage your agency profile</span>
            </div>
          </button>

          {/* Logout */}
          <button className="flex items-center gap-3 p-4 rounded-2xl bg-destructive/10 border border-destructive/20 text-left transition-all active:scale-[0.98] mt-2">
            <LogOut className="w-5 h-5 text-destructive" />
            <span className="text-sm font-medium text-destructive">Sign Out</span>
          </button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

export function BottomNavigation() {
  const location = useLocation(); // Gunakan location untuk deteksi tab aktif

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 safe-bottom bg-background/80 backdrop-blur-xl border-t border-white/5 shadow-[0_-5px_20px_rgba(0,0,0,0.05)]">
      <div className="flex items-center justify-around px-2 h-16 max-w-lg mx-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          // Cek apakah URL sekarang sama dengan path item ini
          const isActive = location.pathname === item.path;

          return (
            <Link
              key={item.id}
              to={item.path}
              className={cn(
                "flex flex-col items-center justify-center gap-1 min-w-[72px] h-12 rounded-xl transition-all duration-300",
                isActive ? "text-orange-400" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <div
                className={cn(
                  "flex items-center justify-center w-11 h-7 rounded-lg transition-all",
                  isActive && "bg-orange-400/10 shadow-[0_0_20px_rgba(251,146,60,0.15)]"
                )}
              >
                <Icon
                  className={cn("w-5 h-5 transition-transform duration-300", isActive && "scale-110")}
                  strokeWidth={isActive ? 2.5 : 2}
                />
              </div>
              <span className={cn(
                "text-[10px] font-bold uppercase tracking-tighter transition-all",
                isActive ? "opacity-100" : "opacity-70"
              )}>
                {item.label}
              </span>
            </Link>
          );
        })}

        <SettingsSheet />
      </div>
    </nav>
  );
}