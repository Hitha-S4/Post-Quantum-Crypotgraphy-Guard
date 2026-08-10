import { useQuery } from '@tanstack/react-query';

export interface TopologyNode {
  node_id: string;
  node_type: 'internal' | 'external';
  hostname: string | null;
  first_seen: string;
  last_seen: string;
  connection_count: number;
  secure_connections: number;
  insecure_connections: number;
  ports: number[];
  protocols: string[];
  firstSeen: string;
  lastSeen: string;
}

export interface TopologyEdge {
  edge_id: string;
  source_ip: string;
  destination_ip: string;
  source_port: number;
  destination_port: number;
  protocol: string;
  first_seen: string;
  last_seen: string;
  connection_count: number;
  security: {
    is_secure: boolean;
    crypto_type: string;
    pqc_status: string;
    confidence: number;
    has_ech: boolean;
    posture: string;
  };
  tls_version: string | null;
  server_name: string | null;
  cipher_suite: string | null;
  bytes_to_server: number;
  bytes_to_client: number;
  total_bytes: number;
  firstSeen: string;
  lastSeen: string;
}

export interface TopologyData {
  timestamp: string;
  timeWindowMinutes: number;
  nodes: Record<string, TopologyNode>;
  edges: Record<string, TopologyEdge>;
  summary: {
    totalNodes: number;
    totalEdges: number;
    secureConnections: number;
    insecureConnections: number;
    unknownConnections: number;
  };
}

const API_BASE_URL = 'http://localhost:8000/api/v1';

async function fetchTopologyData(timeWindow: number = 60): Promise<TopologyData> {
  const response = await fetch(`${API_BASE_URL}/topology/graph?time_window=${timeWindow}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch topology data: ${response.statusText}`);
  }
  
  return response.json();
}

export function useTopologyData(timeWindow: number = 60) {
  return useQuery({
    queryKey: ['topology', timeWindow],
    queryFn: () => fetchTopologyData(timeWindow),
    refetchInterval: 20000, // Refresh every 20 seconds
    staleTime: 15000,
  });
}

// Made with Bob
