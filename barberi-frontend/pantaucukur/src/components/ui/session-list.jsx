// src/components/ui/SessionList.jsx
import React from "react";
import { cn, formatDuration } from "../lib/utils";
import { 
  Armchair, Clock, AlertTriangle, CheckCircle2, Sparkles 
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./tabs";

export function SessionCard({ session, isAnomaly = false }) {
  return (
    <div className={cn(
      "flex items-center gap-4 p-4 rounded-2xl border-t transition-all active:scale-[0.99]",
      isAnomaly ? "bg-amber-500/5 border-amber-500/20" : "bg-primary/5 border-white/10"
    )}>
      <div className={cn(
        "flex items-center justify-center w-12 h-12 rounded-xl shrink-0",
        isAnomaly ? "bg-amber-500/10" : "bg-secondary/50"
      )}>
        <Armchair className={cn("w-6 h-6", isAnomaly ? "text-amber-600" : "text-primary")} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-semibold">{session.chairName}</span>
          <span className={cn(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium",
            isAnomaly ? "bg-amber-500/20 text-amber-600" : "bg-emerald-500/20 text-emerald-600"
          )}>
            {isAnomaly ? <AlertTriangle className="w-3 h-3" /> : <CheckCircle2 className="w-3 h-3" />}
            {isAnomaly ? "System Filtered" : "Valid"}
          </span>
        </div>
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{session.startTime}</span>
          <span className="font-mono font-medium text-foreground">{formatDuration(session.duration)}</span>
        </div>
        {isAnomaly && session.anomalyReason && (
          <div className="flex items-center gap-1.5 mt-2 px-2.5 py-1.5 rounded-lg bg-amber-500/10">
            <Sparkles className="w-3.5 h-3.5 text-amber-500 shrink-0" />
            <span className="text-xs text-amber-700">AI: {session.anomalyReason}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function SessionList({ validSessions, anomalySessions }) {
  return (
    <Tabs defaultValue="valid" className="flex-1 flex flex-col overflow-hidden ">
      <TabsList className="mx-4 mt-4 mb-2 grid grid-cols-2 h-11 rounded-xl bg-secondary/50 p-1 ">
        <TabsTrigger value="valid" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
          Valid ({validSessions.length})
        </TabsTrigger>
        <TabsTrigger value="anomalies" className="rounded-lg data-[state=active]:bg-amber-500 data-[state=active]:text-white">
          Anomalies ({anomalySessions.length})
        </TabsTrigger>
      </TabsList>

      <TabsContent value="valid" className="flex-1 overflow-auto px-4 pb-24 mt-0">
        <div className="flex flex-col gap-3 py-3">
          {validSessions.length > 0 ? (
            validSessions.map((s) => <SessionCard key={s.id} session={s} />)
          ) : (
            <div className="flex flex-col items-center py-12 text-muted-foreground">
              <CheckCircle2 className="w-12 h-12 opacity-20 mb-3" />
              <p className="text-sm">No valid sessions found</p>
            </div>
          )}
        </div>
      </TabsContent>

      <TabsContent value="anomalies" className="flex-1 overflow-auto px-4 pb-24 mt-0">
        <div className="flex flex-col gap-3 py-3  ">
          <div className="flex items-start gap-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20">
            <Sparkles className="w-5 h-5 text-amber-500 mt-0.5" />
            <p className="text-xs text-amber-700 leading-relaxed">Filtered for auditing purposes.</p>
          </div>
          {anomalySessions.length > 0 ? (
            anomalySessions.map((s) => <SessionCard key={s.id} session={s} isAnomaly />)
          ) : (
            <div className="flex flex-col items-center py-12 text-muted-foreground">
              <AlertTriangle className="w-12 h-12 opacity-20 mb-3" />
              <p className="text-sm">No anomalies detected</p>
            </div>
          )}
        </div>
      </TabsContent>
    </Tabs>
  );
}