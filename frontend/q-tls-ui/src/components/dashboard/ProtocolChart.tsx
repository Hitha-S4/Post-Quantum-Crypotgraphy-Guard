import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from 'recharts';

interface ProtocolChartProps {
  data: Record<string, number>;
}

export function ProtocolChart({ data }: ProtocolChartProps) {
  const chartData = Object.entries(data)
    .map(([name, value]) => ({ name: name.toUpperCase(), value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);

  const getBarColor = (name: string) => {
    const colors: Record<string, string> = {
      TLS: 'hsl(199, 100%, 50%)',
      HTTPS: 'hsl(199, 100%, 50%)',
      HTTP: 'hsl(38, 92%, 50%)',
      DNS: 'hsl(180, 100%, 42%)',
      TCP: 'hsl(210, 10%, 55%)',
      UDP: 'hsl(210, 10%, 45%)',
    };
    return colors[name] || 'hsl(210, 10%, 40%)';
  };

  return (
    <div className="carbon-tile h-full">
      <h2 className="text-sm font-semibold mb-4">Protocol Distribution</h2>
      
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
              width={50}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(225, 15%, 12%)',
                border: '1px solid hsl(225, 12%, 20%)',
                borderRadius: '0',
                color: 'hsl(210, 17%, 95%)',
              }}
              formatter={(value: number) => [`${value} flows`, '']}
            />
            <Bar dataKey="value" radius={0}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry.name)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
