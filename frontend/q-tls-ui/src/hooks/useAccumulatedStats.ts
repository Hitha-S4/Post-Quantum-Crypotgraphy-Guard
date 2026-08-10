import { useState, useEffect, useCallback } from 'react';

const API_URL = 'http://localhost:8000/api/v1/accumulated-stats';
const POLL_INTERVAL = 20000; // 20 seconds

export interface AccumulatedStats {
  last_updated: string;
  total_flows: number;
  total_tls_flows: number;
  total_tcp_flows: number;
  total_udp_flows: number;
  total_other_flows: number;
  total_pqc_safe: number;
  total_pqc_vulnerable: number;
  total_pqc_unknown: number;
  total_bytes_to_server: number;
  total_bytes_to_client: number;
  total_bytes: number;
  total_alerts: number;
  total_critical_alerts: number;
  total_high_alerts: number;
  total_medium_alerts: number;
  total_low_alerts: number;
  protocol_distribution: Record<string, number>;
  tls_version_distribution: Record<string, number>;
  cipher_suite_distribution: Record<string, number>;
  key_exchange_distribution: Record<string, number>;
  flow_state_distribution: Record<string, number>;
  posture_distribution: Record<string, number>;
}

export function useAccumulatedStats() {
  const [stats, setStats] = useState<AccumulatedStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch(API_URL);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data: AccumulatedStats = await response.json();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch stats');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchStats]);

  return { stats, loading, error, refresh: fetchStats };
}
