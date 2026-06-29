import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

export const normalizeSession = (s) => ({
      id: s.id,
      chairId: Number(s.chair), // Pastikan Number
      chairName: `Kursi ${s.chair.toString().padStart(2, "0")}`,
      startTime: new Date(s.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      duration: s.duration,
      status: s.status.toLowerCase(),
      anomalyReason: s.duration < 60 ? "Short duration detected" : "Irregular pattern"
    });
