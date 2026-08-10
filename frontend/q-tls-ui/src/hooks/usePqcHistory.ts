import { useState, useEffect, useCallback } from 'react';

const API_URL = 'http://localhost:8000/api/v1/pqc-status-history';

export interface PqcHistoryDataPoint {
  timestamp: string;
  pqcSafe: number;
  pqcVulnerable: number;
  pqcUnknown: number;
  total: number;
}

export interface PqcHistoryResponse {
  timeRange: {
    start: string;
    end: string;
    hours: number;
    intervalMinutes: number;
  };
  dataPoints: PqcHistoryDataPoint[];
  summary: {
    totalDataPoints: number;
    avgPqcSafe: number;
    avgPqcVulnerable: number;
    avgPqcSafePercentage: number;
    trend: string;
  };
}

const POLL_INTERVAL = 60000; // 60 seconds

export function usePqcHistory(hours = 24, intervalMinutes = 60) {
  const [data, setData] = useState<PqcHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch(`${API_URL}?hours=${hours}&interval_minutes=${intervalMinutes}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result: PqcHistoryResponse = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch history');
    } finally {
      setLoading(false);
    }
  }, [hours, intervalMinutes]);

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchHistory]);

  return { data, loading, error, refresh: fetchHistory };
}
