import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from 'recharts';

interface KeyExchangeChartProps {
  data: Record<string, number>;
}

export function KeyExchangeChart({ data }: KeyExchangeChartProps) {
  const chartData = Object.entries(data)
    .map(([name, value]) => ({ 
      name: name.replace('Unknown_', '').replace('_', '-'), 
      value,
      isPQC: name.includes('ML_KEM') || name.includes('Kyber')
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  const getBarColor = (entry: { name: string; isPQC: boolean }) => {
    if (entry.isPQC) {
      return 'hsl(145, 80%, 42%)'; // Green for PQC algorithms
    }
    if (entry.name.includes('X25519') || entry.name.includes('X448')) {
      return 'hsl(38, 92%, 50%)'; // Orange for classical ECDH
    }
    return 'hsl(210, 10%, 55%)'; // Gray for unknown
  };

  return (
    <div className="carbon-tile h-full">
      <h2 className="text-sm font-semibold mb-4">Key Exchange Distribution</h2>
      
      <div className="h-[240px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20 }}>
            <XAxis 
              type="number" 
              axisLine={false}
              tickLine={false}
              tick={{ fill: 'hsl(210, 10%, 55%)', fontSize: 10 }}
            />
            <YAxis 
              type="category" 
              dataKey="name" 
              axisLine={false}
              tickLine={false}
              tick={{ fill: 'hsl(210, 17%, 95%)', fontSize: 11 }}
              width={80}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(225, 15%, 12%)',
                border: '1px solid hsl(225, 12%, 20%)',
                borderRadius: '0',
                color: 'hsl(210, 17%, 95%)',
              }}
              formatter={(value: number) => [`${value} connections`, '']}
            />
            <Bar dataKey="value" radius={0}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      
      <div className="flex items-center justify-center gap-4 mt-4 pt-4 border-t border-border">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 bg-success" />
          <span className="text-xs text-muted-foreground">PQC</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 bg-warning" />
          <span className="text-xs text-muted-foreground">Classical</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3" style={{ backgroundColor: 'hsl(210, 10%, 55%)' }} />
          <span className="text-xs text-muted-foreground">Unknown</span>
        </div>
      </div>
    </div>
  );
}

// Made with Bob
