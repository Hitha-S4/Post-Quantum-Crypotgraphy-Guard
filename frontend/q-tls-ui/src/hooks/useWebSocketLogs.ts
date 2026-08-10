import { useState, useEffect, useRef, useCallback } from 'react';
import { ProcessedLog, PQCStatus, determinePQCStatus } from '@/data/sampleLogs';

const WS_URL = 'ws://localhost:8000/ws/kafka-stream';
const MAX_LOGS = 50;

interface ExchangeGroups {
  pqc_groups: string[];
  hybrid_groups: string[];
  classical_groups: string[];
  total_groups: number;
  has_pqc: boolean;
}

interface Algorithms {
  supported_groups: string[];
  key_share_groups: string[];
  signature_algorithms: string[];
  cipher_suites: string[];
}

interface PQCDetection {
  status: string;
  crypto_type: string;
  posture: string;
  has_ech: boolean;
  is_pqc_safe: boolean;
  algorithms?: Algorithms;
  // Legacy fields for backward compatibility
  confidence?: number;
  detection_method?: string;
  exchange_groups?: ExchangeGroups;
}

interface FlowData {
  bytes_toserver?: number;
  bytes_toclient?: number;
  total_bytes?: number;
  state?: string;
  pkts_toserver?: number;
  pkts_toclient?: number;
  start?: string;
  end?: string;
  age?: number;
  reason?: string;
  alerted?: boolean;
}

interface KafkaDataPayload {
  src_ip: string;
  src_port: number;
  dest_ip: string;
  dest_port: number;
  proto: string;
  flow_id: number;
  event_type: string;
  ip_v: number;
  in_iface: string;
  timestamp?: string;
  hostname?: string;
  dns?: Record<string, unknown>;
  tls?: Record<string, unknown>;
  app_proto?: string;
  flow?: FlowData;
  pqc_detection?: PQCDetection;
}

interface KafkaMessage {
  type: string;
  data: {
    type?: string;
    timestamp?: string;
    data?: KafkaDataPayload;
    // Support direct data format (without nested data)
    src_ip?: string;
    src_port?: number;
    dest_ip?: string;
    dest_port?: number;
    proto?: string;
    flow_id?: number;
    event_type?: string;
    ip_v?: number;
    in_iface?: string;
    app_proto?: string;
    flow?: FlowData;
    pqc_detection?: PQCDetection;
  };
  timestamp: string;
}

function kafkaToProcessedLog(msg: KafkaMessage): ProcessedLog {
  // Handle nested data structure from backend
  const actualData: KafkaDataPayload = (msg.data.data || msg.data) as KafkaDataPayload;
  
  const flowData = {
    pkts_toserver: actualData.flow?.pkts_toserver ?? 0,
    pkts_toclient: actualData.flow?.pkts_toclient ?? 0,
    bytes_toserver: actualData.flow?.bytes_toserver ?? 0,
    bytes_toclient: actualData.flow?.bytes_toclient ?? 0,
    start: actualData.flow?.start ?? actualData.timestamp ?? msg.timestamp,
    end: actualData.flow?.end ?? actualData.timestamp ?? msg.timestamp,
    age: actualData.flow?.age ?? 0,
    state: actualData.flow?.state ?? 'new',
    reason: actualData.flow?.reason ?? '',
    alerted: actualData.flow?.alerted ?? false,
  };

  const baseLog = {
    timestamp: actualData.timestamp || msg.data.timestamp || msg.timestamp || new Date().toISOString(),
    flow_id: actualData.flow_id,
    in_iface: actualData.in_iface || 'unknown',
    event_type: actualData.event_type,
    src_ip: actualData.src_ip,
    src_port: actualData.src_port,
    dest_ip: actualData.dest_ip,
    dest_port: actualData.dest_port,
    ip_v: actualData.ip_v ?? 4,
    proto: actualData.proto,
    app_proto: actualData.event_type === 'dns' ? 'dns' : (actualData.app_proto as string | undefined),
    hostname: actualData.hostname,
    flow: flowData,
    tls: actualData.tls as any,
    pqc_detection: actualData.pqc_detection,
    rawPayload: msg,
  };

  // Use backend PQC detection if available, otherwise fall back to frontend logic
  let status: PQCStatus;
  let reason: string;

  if (actualData.pqc_detection) {
    const pqcDetection = actualData.pqc_detection;
    
    // Map backend status to frontend PQCStatus type based on is_pqc_safe flag
    if (pqcDetection.is_pqc_safe === true) {
      status = 'safe';
      const cryptoType = pqcDetection.crypto_type !== 'unknown' ? pqcDetection.crypto_type.toUpperCase() : 'PQC';
      const confidenceStr = pqcDetection.confidence ? ` (${Math.round(pqcDetection.confidence * 100)}% confidence)` : '';
      reason = `${cryptoType} - PQC Safe${confidenceStr}`;
    } else if (pqcDetection.is_pqc_safe === false) {
      status = 'vulnerable';
      const cryptoType = pqcDetection.crypto_type !== 'unknown' ? pqcDetection.crypto_type.toUpperCase() : 'Classical';
      const confidenceStr = pqcDetection.confidence ? ` (${Math.round(pqcDetection.confidence * 100)}% confidence)` : '';
      reason = `${cryptoType} - Quantum Vulnerable${confidenceStr}`;
    } else {
      // is_pqc_safe is null/undefined - don't show "unknown" protocol
      status = 'unknown';
      reason = 'N/A';
    }
  } else {
    // Fallback to frontend heuristic logic
    const result = determinePQCStatus(baseLog);
    status = result.status;
    reason = result.reason;
  }

  return {
    ...baseLog,
    pqcStatus: status,
    pqcReason: reason,
  };
}

export function useWebSocketLogs() {
  const [logs, setLogs] = useState<ProcessedLog[]>([]);
  const [connected, setConnected] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pausedRef = useRef(false);

  // Keep ref in sync
  useEffect(() => {
    pausedRef.current = isPaused;
  }, [isPaused]);

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);

      ws.onmessage = (event) => {
        if (pausedRef.current) return;
        try {
          const msg: KafkaMessage = JSON.parse(event.data);
          if (msg.type === 'kafka_message' && msg.data) {
            // Get the actual data (handle nested structure)
            const actualData = (msg.data.data || msg.data) as KafkaDataPayload;
            
            // Filter out stats events and other non-flow events
            if (actualData.event_type === 'stats') {
              return;
            }
            
            const processed = kafkaToProcessedLog(msg);
            setLogs(prev => [processed, ...prev].slice(0, MAX_LOGS));
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        setConnected(false);
        // Reconnect after 3s
        setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return { logs, connected, isPaused, setIsPaused };
}
