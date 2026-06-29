
import { cn } from "./lib/utils";
import { Crown, Trophy, Timer, User2 } from "lucide-react";


const mockBarbers = [
  { id: 1, name: "Ahmad", totalHeads: 18, avgSpeed: 22 },
  { id: 2, name: "Budi", totalHeads: 15, avgSpeed: 28 },
  { id: 3, name: "Zaim", totalHeads: 12, avgSpeed: 30 },
];

function RankBadge({ rank }) {
  if (rank === 1) {
    return (
      <div className="flex items-center justify-center w-6 h-6 rounded-full bg-chair-occupied-border/20">
        <Crown className="w-3.5 h-3.5 text-chair-occupied-text" />
      </div>
    );
  }
  return (
    <span className="flex items-center justify-center w-6 h-6 text-xs font-mono font-bold text-muted-foreground bg-secondary/30 rounded-full">
      {rank}
    </span>
  );
}

export function BarberLeaderboard() {
  return (
    <div className="space-y-3 mt-5">
      {/* Section Header */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <Trophy className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">
            Barber Leaderboard
          </span>
        </div>
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">
          Today
        </span>
      </div>

      {/* Grid List of Cards */}
      <div className="flex flex-col gap-3">
        {mockBarbers.map((barber, index) => {
          const rank = index + 1;
          const isTopPerformer = rank === 1;

          return (
            <div
              key={barber.id}
              className={cn(
                "relative flex items-center gap-4 p-4 rounded-2xl transition-all duration-200",
                "border-t-1 bg-card shadow-sm",
                isTopPerformer
                  ? "border-t-chair-occupied-border border-x-white/5 border-b-white/5 active-shimmer bg-[var(--chair-occupied)]"
                  : "border-t-white/10 border-x-white/5 border-b-white/5"
              )}
            >
              {/* Rank Badge */}
              <div className="relative z-10 shrink-0">
                <RankBadge rank={rank} />
              </div>

              {/* Barber Info */}
              <div className="relative z-10 flex flex-1 items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-secondary/50 flex items-center justify-center border border-white/5">
                  <User2 className={cn(
                    "w-5 h-5",
                    isTopPerformer ? "text-chair-occupied-text" : "text-muted-foreground"
                  )} />
                </div>
                <div className="flex flex-col">
                  <span className={cn(
                    "text-sm font-bold",
                    isTopPerformer ? "text-chair-occupied-text" : "text-foreground"
                  )}>
                    {barber.name}
                  </span>
                  <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                    <Timer className="w-3 h-3" /> {barber.avgSpeed}m avg speed
                  </span>
                </div>
              </div>

              {/* Stats heads */}
              <div className="relative z-10 flex flex-col items-end">
                <span className={cn(
                  "text-xl font-mono font-black leading-none",
                  isTopPerformer ? "text-chair-occupied-text" : "text-foreground"
                )}>
                  {barber.totalHeads}
                </span>
                <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-tighter">
                  Heads
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}