import { useState, useEffect, useCallback, useRef } from 'react';

export interface Alert {
  id: string;
  message: string;
  severity: 'high' | 'medium' | 'low';
  time: string;
  destIp: string;
  timestamp?: number;
  read?: boolean;
}

interface UseAlertsReturn {
  alerts: Alert[];
  unreadCount: number;
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  markAsRead: (alertId: string) => void;
  markAllAsRead: () => void;
  refetch: () => void;
}

const API_BASE_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws/alerts';

export function useAlerts(): UseAlertsReturn {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  // Fetch alerts from API
  const fetchAlerts = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE_URL}/api/v1/alerts/list`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Transform API data to match Alert interface
      const transformedAlerts: Alert[] = (data.alerts || []).map((alert: any) => ({
        id: alert.id || String(Date.now() + Math.random()),
        message: alert.description || alert.message || alert.title || 'Unknown alert',
        severity: (alert.severity || 'medium').toLowerCase() as 'high' | 'medium' | 'low',
        time: alert.timestamp ? new Date(alert.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString(),
        destIp: alert.destination_ip || alert.dest_ip || 'N/A',
        timestamp: alert.timestamp ? new Date(alert.timestamp).getTime() : Date.now(),
        read: alert.acknowledged || false,
      }));
      
      setAlerts(transformedAlerts);
      setUnreadCount(transformedAlerts.filter(a => !a.read).length);
      setIsLoading(false);
    } catch (err) {
      console.error('Error fetching alerts:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch alerts');
      setIsLoading(false);
    }
  }, []);

  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(WS_URL);
      
      ws.onopen = () => {
        console.log('WebSocket connected to alerts');
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle new alert from WebSocket
          const newAlert: Alert = {
            id: data.id || String(Date.now() + Math.random()),
            message: data.description || data.message || data.title || 'New alert',
            severity: (data.severity || 'medium').toLowerCase() as 'high' | 'medium' | 'low',
            time: data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString(),
            destIp: data.destination_ip || data.dest_ip || 'N/A',
            timestamp: data.timestamp ? new Date(data.timestamp).getTime() : Date.now(),
            read: false,
          };

          setAlerts(prev => [newAlert, ...prev]);
          setUnreadCount(prev => prev + 1);
          
          // Optional: Show browser notification
          if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('New Security Alert', {
              body: newAlert.message,
              icon: '/favicon.ico',
            });
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('WebSocket connection error');
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        wsRef.current = null;

        // Attempt to reconnect
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, delay);
        } else {
          setError('WebSocket connection failed after multiple attempts');
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Error creating WebSocket:', err);
      setError('Failed to create WebSocket connection');
    }
  }, []);

  // Mark alert as read
  const markAsRead = useCallback((alertId: string) => {
    setAlerts(prev => 
      prev.map(alert => 
        alert.id === alertId ? { ...alert, read: true } : alert
      )
    );
    setUnreadCount(prev => Math.max(0, prev - 1));
  }, []);

  // Mark all alerts as read
  const markAllAsRead = useCallback(() => {
    setAlerts(prev => prev.map(alert => ({ ...alert, read: true })));
    setUnreadCount(0);
  }, []);

  // Initialize
  useEffect(() => {
    fetchAlerts();
    connectWebSocket();

    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }

    // Cleanup
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [fetchAlerts, connectWebSocket]);

  return {
    alerts,
    unreadCount,
    isConnected,
    isLoading,
    error,
    markAsRead,
    markAllAsRead,
    refetch: fetchAlerts,
  };
}

// Made with Bob
