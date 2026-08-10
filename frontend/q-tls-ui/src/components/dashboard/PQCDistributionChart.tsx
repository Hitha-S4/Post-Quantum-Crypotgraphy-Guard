import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface PQCDistributionChartProps {
  data: Record<string, number>;
}

export function PQCDistributionChart({ data }: PQCDistributionChartProps) {
  const postureColors: Record<string, string> = {
    ECH_PROTECTED: 'hsl(145, 80%, 42%)',
    PQC: 'hsl(145, 80%, 42%)',
    PQC_SAFE: 'hsl(145, 80%, 42%)',
    SAFE: 'hsl(145, 80%, 42%)',
    HYBRID: 'hsl(190, 95%, 45%)',
    CLASSICAL: 'hsl(0, 72%, 51%)',
    VULNERABLE: 'hsl(0, 72%, 51%)',
    UNKNOWN_PQC: 'hsl(38, 92%, 50%)',
    UNKNOWN: 'hsl(38, 92%, 50%)',
  };

  const postureLabels: Record<string, string> = {
    ECH_PROTECTED: 'ECH Protected',
    PQC: 'PQC',
    PQC_SAFE: 'PQC Safe',
    SAFE: 'PQC Safe',
    HYBRID: 'Hybrid',
    CLASSICAL: 'Classical',
    VULNERABLE: 'Vulnerable',
    UNKNOWN_PQC: 'Unknown',
    UNKNOWN: 'Unknown',
  };

  const chartData = Object.entries(data)
    .map(([name, value]) => ({
      name: postureLabels[name] || name.replace(/_/g, ' '),
      value,
      color: postureColors[name] || 'hsl(210, 17%, 50%)',
    }))
    .filter((item) => item.value > 0);

  const total = Object.values(data).reduce((sum, val) => sum + val, 0);

  return (
    <div className="carbon-tile h-full flex flex-col">
      <h2 className="text-sm font-semibold mb-3">Posture Distribution</h2>
      
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={2}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} stroke="transparent" />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(225, 15%, 12%)',
                border: '1px solid hsl(225, 12%, 20%)',
                borderRadius: '0',
                color: 'hsl(210, 17%, 95%)',
              }}
              formatter={(value: number) => `${value} (${((value / total) * 100).toFixed(1)}%)`}
            />
            <Legend
              verticalAlign="bottom"
              height={36}
              formatter={(value) => (
                <span className="text-xs text-muted-foreground">{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      
      <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-border">
        {chartData.map((item) => (
          <div key={item.name} className="text-center">
            <p className="text-lg font-light" style={{ color: item.color }}>{item.value}</p>
            <p className="text-[10px] uppercase text-muted-foreground leading-tight">{item.name}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
