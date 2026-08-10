import { Notification } from '@carbon/icons-react';
import { useState, useRef, useEffect } from 'react';
import { useAlerts } from '@/hooks/useAlerts';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Time } from '@carbon/icons-react';

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { alerts, unreadCount, isConnected, markAsRead, markAllAsRead } = useAlerts();

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const severityColors = {
    high: 'bg-destructive',
    medium: 'bg-warning',
    low: 'bg-primary',
  };

  const recentAlerts = alerts.slice(0, 10);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 hover:bg-muted transition-colors relative"
        title={`${unreadCount} unread alerts`}
      >
        <Notification size={20} className={isConnected ? 'text-muted-foreground' : 'text-warning'} />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-destructive opacity-75"></span>
            <span className="relative inline-flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-white">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-96 bg-background border border-border rounded-lg shadow-lg z-50">
          <div className="flex items-center justify-between p-4 border-b border-border">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold">Notifications</h3>
              {!isConnected && (
                <Badge variant="outline" className="text-xs">
                  Offline
                </Badge>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-xs text-primary hover:underline"
              >
                Mark all as read
              </button>
            )}
          </div>

          <ScrollArea className="h-[400px]">
            {recentAlerts.length > 0 ? (
              <div className="divide-y divide-border">
                {recentAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    onClick={() => {
                      if (!alert.read) {
                        markAsRead(alert.id);
                      }
                    }}
                    className={`p-4 hover:bg-muted/50 transition-colors cursor-pointer ${
                      !alert.read ? 'bg-muted/30' : ''
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span
                        className={`w-2 h-2 mt-1.5 rounded-full flex-shrink-0 ${severityColors[alert.severity]}`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <p className="text-sm font-medium text-foreground line-clamp-2">
                            {alert.message}
                          </p>
                          {!alert.read && (
                            <span className="w-2 h-2 rounded-full bg-primary flex-shrink-0 mt-1" />
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span className="font-mono truncate">{alert.destIp}</span>
                          <span className="flex items-center gap-1 flex-shrink-0">
                            <Time size={12} />
                            {alert.time}
                          </span>
                        </div>
                        <Badge
                          variant={alert.severity === 'high' ? 'destructive' : 'secondary'}
                          className="mt-2 text-xs"
                        >
                          {alert.severity}
                        </Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-[200px] text-muted-foreground">
                <Notification size={32} className="mb-2 opacity-50" />
                <p className="text-sm">No notifications</p>
              </div>
            )}
          </ScrollArea>

          {alerts.length > 10 && (
            <div className="p-3 border-t border-border text-center">
              <button className="text-xs text-primary hover:underline">
                View all {alerts.length} alerts
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Made with Bob
