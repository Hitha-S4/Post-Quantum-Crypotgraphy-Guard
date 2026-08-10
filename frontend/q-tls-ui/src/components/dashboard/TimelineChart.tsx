import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from 'recharts';
import { PqcHistoryResponse } from '@/hooks/usePqcHistory';

interface TimelineChartProps {
  data: PqcHistoryResponse | null;
  loading?: boolean;
  error?: string | null;
}

export function TimelineChart({ data, loading, error }: TimelineChartProps) {
  const chartData = (data?.dataPoints ?? []).map((dp) => ({
    time: new Date(dp.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }),
    safe: dp.pqcSafe,
    vulnerable: dp.pqcVulnerable,
    unknown: dp.pqcUnknown,
    total: dp.total,
  }));

  const timeLabel = data ? `Last ${data.timeRange.hours}h · ${data.timeRange.intervalMinutes}m intervals` : 'Last 4 hours';

  return (
    <div className="carbon-tile h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold">PQC Status Over Time</h2>
        <div className="flex items-center gap-3">
          {data?.summary && (
            <span className="text-[10px] text-muted-foreground uppercase">
              Trend: {data.summary.trend}
            </span>
          )}
          <span className="text-xs text-muted-foreground">{timeLabel}</span>
        </div>
      </div>
      
      <div className="h-[200px]">
        {loading && chartData.length === 0 ? (
          <div className="flex items-center justify-center h-full text-xs text-muted-foreground">Loading history...</div>
        ) : error && chartData.length === 0 ? (
          <div className="flex items-center justify-center h-full text-xs text-destructive">Error: {error}</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorSafe" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(145, 80%, 42%)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="hsl(145, 80%, 42%)" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorVulnerable" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(0, 72%, 51%)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="hsl(0, 72%, 51%)" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorUnknown" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(38, 92%, 50%)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="hsl(38, 92%, 50%)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis 
                dataKey="time" 
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'hsl(210, 10%, 55%)', fontSize: 10 }}
              />
              <YAxis 
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'hsl(210, 10%, 55%)', fontSize: 10 }}
                width={30}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(225, 15%, 12%)',
                  border: '1px solid hsl(225, 12%, 20%)',
                  borderRadius: '0',
                  color: 'hsl(210, 17%, 95%)',
                }}
              />
              <Area type="monotone" dataKey="safe" stroke="hsl(145, 80%, 42%)" strokeWidth={2} fillOpacity={1} fill="url(#colorSafe)" name="PQC Safe" />
              <Area type="monotone" dataKey="vulnerable" stroke="hsl(0, 72%, 51%)" strokeWidth={2} fillOpacity={1} fill="url(#colorVulnerable)" name="Vulnerable" />
              <Area type="monotone" dataKey="unknown" stroke="hsl(38, 92%, 50%)" strokeWidth={2} fillOpacity={1} fill="url(#colorUnknown)" name="Unknown" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
      
      <div className="flex items-center justify-center gap-6 mt-4 pt-4 border-t border-border">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 bg-success" />
          <span className="text-xs text-muted-foreground">PQC Safe</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 bg-destructive" />
          <span className="text-xs text-muted-foreground">Vulnerable</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 bg-warning" />
          <span className="text-xs text-muted-foreground">Unknown</span>
        </div>
      </div>
    </div>
  );
}
