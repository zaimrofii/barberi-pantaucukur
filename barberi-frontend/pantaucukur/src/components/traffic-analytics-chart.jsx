"use client";

import { BarChart3 } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Cell,
} from "recharts";

// Mock data with 12 data points (09:00 to 21:00) with peak at 17:00-19:00
const trafficData = [
  { hour: "09:00", customers: 2 },
  { hour: "10:00", customers: 3 },
  { hour: "11:00", customers: 4 },
  { hour: "12:00", customers: 6 },
  { hour: "13:00", customers: 5 },
  { hour: "14:00", customers: 4 },
  { hour: "15:00", customers: 5 },
  { hour: "16:00", customers: 7 },
  { hour: "17:00", customers: 9 },
  { hour: "18:00", customers: 10 },
  { hour: "19:00", customers: 8 },
  { hour: "20:00", customers: 4 },
];

// OKLCH colors converted to hex for Recharts compatibility
const CHART_HIGH = "#d4915a"; // oklch(0.65 0.18 45) - Orange/Amber
const CHART_LOW = "#5b8dbd";  // oklch(0.55 0.15 220) - Electric Blue

function getBarColor(count) {
  return count > 5 ? CHART_HIGH : CHART_LOW;
}

export function TrafficAnalyticsChart() {
  const totalCustomers = trafficData.reduce((sum, d) => sum + d.customers, 0);
  const peakHour = trafficData.reduce((max, d) =>
    d.customers > max.customers ? d : max
  );

  return (
    <div className="p-4 rounded-2xl bg-card border-t-1 border-white/10 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">
            Traffic Analytics
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Peak:</span>
          <span className="text-xs font-semibold text-chair-occupied-text">
            {peakHour.hour}
          </span>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-3xl font-bold text-foreground tracking-tight">
          {totalCustomers}
        </span>
        <span className="text-sm text-muted-foreground">customers today</span>
      </div>

      {/* Chart */}
      <div className="h-40 -mx-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={trafficData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="oklch(0.25 0.01 260)"
            />
            <XAxis
              dataKey="hour"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: "oklch(0.6 0 0)" }}
              tickFormatter={(value) => value.replace(":00", "")}
              interval={2}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: "oklch(0.6 0 0)" }}
              width={30}
            />
            <Bar
              dataKey="customers"
              radius={[4, 4, 0, 0]}
              maxBarSize={24}
            >
              {trafficData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry.customers)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 mt-3 pt-3 border-t border-border">
        <div className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded-sm"
            style={{ backgroundColor: CHART_HIGH }}
          />
          <span className="text-xs text-muted-foreground">High traffic (&gt;5)</span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded-sm"
            style={{ backgroundColor: CHART_LOW }}
          />
          <span className="text-xs text-muted-foreground">Normal</span>
        </div>
      </div>
    </div>
  );
}
