import { useMemo } from 'react';
import {
  Network_3,
  Security,
  DataBase,
  WarningAlt,
  ChartArea,
  Renew
} from '@carbon/icons-react';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { StatTile } from '@/components/dashboard/StatTile';
import { LiveLogTable } from '@/components/dashboard/LiveLogTable';
import { PQCDistributionChart } from '@/components/dashboard/PQCDistributionChart';
import { ProtocolChart } from '@/components/dashboard/ProtocolChart';
import { TimelineChart } from '@/components/dashboard/TimelineChart';
import { RecentAlerts } from '@/components/dashboard/RecentAlerts';
import { KeyExchangeChart } from '@/components/dashboard/KeyExchangeChart';
import { TLSVersionChart } from '@/components/dashboard/TLSVersionChart';
import { AgentChatButton } from '@/components/dashboard/AgentChatButton';
import { useAccumulatedStats } from '@/hooks/useAccumulatedStats';
import { useWebSocketLogs } from '@/hooks/useWebSocketLogs';
import { usePqcHistory } from '@/hooks/usePqcHistory';
import { useAlerts } from '@/hooks/useAlerts';

const Index = () => {
  const { stats, loading, error, refresh } = useAccumulatedStats();

  const { logs, connected, isPaused, setIsPaused } = useWebSocketLogs();
  const { data: pqcHistory, loading: historyLoading, error: historyError } = usePqcHistory(4, 5);
  const { alerts } = useAlerts();

  const derivedTlsStatus = useMemo(() => {
    const safe = logs.filter((log) => log.pqcStatus === 'safe').length;
    const vulnerable = logs.filter((log) => log.pqcStatus === 'vulnerable').length;
    const unknown = logs.filter((log) => log.pqcStatus === 'unknown').length;

    return {
      safe,
      vulnerable,
      unknown,
      total: safe + vulnerable + unknown,
    };
  }, [logs]);

  const postureDistribution = useMemo(() => {
    const apiPostureDistribution = stats?.posture_distribution ?? {};
    const filteredApiPostureDistribution = Object.fromEntries(
      Object.entries(apiPostureDistribution).filter(([key, value]) => {
        if (value <= 0) {
          return false;
        }

        return !['UNKNOWN', 'UNKNOWN_PQC'].includes(key) || Object.keys(apiPostureDistribution).length === 1;
      }),
    );
    const totalFromApi = Object.values(filteredApiPostureDistribution).reduce((sum, value) => sum + value, 0);

    if (totalFromApi > 0) {
      return filteredApiPostureDistribution;
    }

    if (derivedTlsStatus.safe > 0 || derivedTlsStatus.vulnerable > 0) {
      return {
        PQC_SAFE: derivedTlsStatus.safe,
        VULNERABLE: derivedTlsStatus.vulnerable,
      };
    }

    if (derivedTlsStatus.unknown > 0) {
      return {
        UNKNOWN: derivedTlsStatus.unknown,
      };
    }

    return {};
  }, [stats, derivedTlsStatus]);

  const protocolDistribution = useMemo(() => {
    return stats?.protocol_distribution ?? {};
  }, [stats]);

  const keyExchangeDistribution = useMemo(() => {
    return stats?.key_exchange_distribution ?? {};
  }, [stats]);

  const tlsVersionDistribution = useMemo(() => {
    return stats?.tls_version_distribution ?? {};
  }, [stats]);

  const totalPqcSafe = useMemo(() => {
    return (stats?.total_pqc_safe ?? 0) > 0 ? (stats?.total_pqc_safe ?? 0) : derivedTlsStatus.safe;
  }, [stats, derivedTlsStatus.safe]);

  const totalPqcVulnerable = useMemo(() => {
    return (stats?.total_pqc_vulnerable ?? 0) > 0
      ? (stats?.total_pqc_vulnerable ?? 0)
      : derivedTlsStatus.vulnerable;
  }, [stats, derivedTlsStatus.vulnerable]);

  // Get recent alerts (limit to 5 for the dashboard)
  const recentAlerts = useMemo(() => {
    return alerts.slice(0, 5);
  }, [alerts]);

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <DashboardHeader />
      
      <main className="flex-1 p-4 space-y-4">
        {/* Refresh bar */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {error && (
              <span className="text-xs text-destructive">API Error: {error}</span>
            )}
            {stats && (
              <span className="text-xs text-muted-foreground">
                Last updated: {new Date(stats.last_updated).toLocaleTimeString()}
              </span>
            )}
          </div>
          <button
            onClick={refresh}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            title="Refresh stats"
          >
            <Renew size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatTile
            value={(stats?.total_flows ?? 0).toLocaleString()}
            label="Total Flows"
            helper={`TCP: ${stats?.total_tcp_flows ?? 0} · UDP: ${stats?.total_udp_flows ?? 0} · Other: ${stats?.total_other_flows ?? 0}`}
            icon={<Network_3 size={24} />}
          />
          <StatTile
            value={(stats?.total_tls_flows ?? 0).toLocaleString()}
            label="TLS Connections"
            helper={`Total bytes: ${formatBytes(stats?.total_bytes ?? 0)}`}
            icon={<Security size={24} />}
            variant="default"
          />
          <StatTile
            value={totalPqcSafe.toLocaleString()}
            label="PQC Safe"
            helper="Quantum-resistant connections"
            icon={<DataBase size={24} />}
            variant="success"
          />
          <StatTile
            value={totalPqcVulnerable.toLocaleString()}
            label="Vulnerable"
            helper="Require migration to PQC"
            icon={<WarningAlt size={24} />}
            variant="danger"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 h-[400px]">
            <LiveLogTable logs={logs} connected={connected} isPaused={isPaused} setIsPaused={setIsPaused} />
          </div>
          <div className="h-[400px]">
            <PQCDistributionChart data={postureDistribution} />
          </div>
        </div>

        {/* Second Row - Analytics */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 -mt-2">
          <div className="lg:col-span-2">
            <TimelineChart data={pqcHistory} loading={historyLoading} error={historyError} />
          </div>
          <div>
            <ProtocolChart data={protocolDistribution} />
          </div>
        </div>

        {/* Third Row - TLS Analytics */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <KeyExchangeChart data={keyExchangeDistribution} />
          <TLSVersionChart data={tlsVersionDistribution} />
        </div>

        {/* Alerts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <RecentAlerts alerts={recentAlerts} />
          <div className="carbon-tile">
            <div className="flex items-center gap-2 mb-4">
              <ChartArea size={16} className="text-primary" />
              <h2 className="text-sm font-semibold">Flow State Distribution</h2>
            </div>
            <div className="space-y-4">
              {stats?.flow_state_distribution && Object.entries(stats.flow_state_distribution).map(([state, count]) => {
                const total = Object.values(stats.flow_state_distribution).reduce((a, b) => a + b, 0);
                const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                return (
                  <div key={state}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-muted-foreground capitalize">{state}</span>
                      <span className="text-foreground">{count} ({pct}%)</span>
                    </div>
                    <div className="h-2 bg-muted overflow-hidden">
                      <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
              {stats && (
                <p className="text-xs text-muted-foreground pt-2 border-t border-border">
                  Total alerts: {stats.total_alerts} (Critical: {stats.total_critical_alerts})
                </p>
              )}
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-border px-4 py-3 flex items-center justify-between text-xs text-muted-foreground">
        <span>TLS PQC Compatibility Monitor v1.0.0</span>
        <span>Auto-refresh: 20s</span>
      </footer>
      
      {/* AI Agent Chat Button */}
      <AgentChatButton />
    </div>
  );
};

export default Index;
