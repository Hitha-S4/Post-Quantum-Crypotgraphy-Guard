import { WarningAlt, Time, ChevronRight } from '@carbon/icons-react';

interface Alert {
  id: string;
  message: string;
  severity: 'high' | 'medium' | 'low';
  time: string;
  destIp: string;
}

interface RecentAlertsProps {
  alerts: Alert[];
}

export function RecentAlerts({ alerts }: RecentAlertsProps) {
  const severityColors = {
    high: 'bg-destructive',
    medium: 'bg-warning',
    low: 'bg-primary',
  };

  return (
    <div className="carbon-tile h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <WarningAlt size={16} className="text-warning" />
          <h2 className="text-sm font-semibold">Security Alerts</h2>
        </div>
        <span className="text-xs text-muted-foreground">{alerts.length} active</span>
      </div>

      <div className="space-y-2">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className="flex items-start gap-3 p-3 bg-muted/50 hover:bg-muted transition-colors cursor-pointer group"
          >
            <span className={`w-1.5 h-1.5 mt-1.5 rounded-full ${severityColors[alert.severity]}`} />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-foreground truncate">{alert.message}</p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-muted-foreground font-mono">{alert.destIp}</span>
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Time size={12} />
                  {alert.time}
                </span>
              </div>
            </div>
            <ChevronRight size={16} className="text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        ))}

        {alerts.length === 0 && (
          <div className="text-center py-8 text-muted-foreground text-sm">
            No active alerts
          </div>
        )}
      </div>
    </div>
  );
}
