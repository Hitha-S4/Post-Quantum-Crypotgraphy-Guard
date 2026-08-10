import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface TLSVersionChartProps {
  data: Record<string, number>;
}

export function TLSVersionChart({ data }: TLSVersionChartProps) {
  const chartData = Object.entries(data)
    .map(([name, value]) => ({
      name: name.replace('_', ' '),
      value,
      color: getVersionColor(name)
    }))
    .filter(item => item.value > 0)
    .sort((a, b) => b.value - a.value);

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  function getVersionColor(version: string): string {
    const colors: Record<string, string> = {
      'TLS_1_3': 'hsl(145, 80%, 42%)', // Green for TLS 1.3
      'TLS_1_2': 'hsl(38, 92%, 50%)',  // Orange for TLS 1.2
      'TLS_1_1': 'hsl(0, 72%, 51%)',   // Red for TLS 1.1
      'TLS_1_0': 'hsl(0, 72%, 51%)',   // Red for TLS 1.0
      'SSL_3_0': 'hsl(0, 72%, 51%)',   // Red for SSL 3.0
    };
    return colors[version] || 'hsl(210, 10%, 55%)';
  }

  return (
    <div className="carbon-tile h-full">
      <h2 className="text-sm font-semibold mb-4">TLS Version Distribution</h2>
      
      <div className="h-[200px]">
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
              formatter={(value: number) => [`${value} (${((value / total) * 100).toFixed(1)}%)`, '']}
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
      
      <div className="grid grid-cols-2 gap-2 mt-4 pt-4 border-t border-border">
        {chartData.slice(0, 4).map((item) => (
          <div key={item.name} className="text-center">
            <p className="text-lg font-light" style={{ color: item.color }}>{item.value}</p>
            <p className="text-[10px] uppercase text-muted-foreground">{item.name}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// Made with Bob
