export interface ExchangeGroups {
  pqc_groups: string[];
  hybrid_groups: string[];
  classical_groups: string[];
  total_groups: number;
  has_pqc: boolean;
}

export interface Algorithms {
  supported_groups: string[];
  key_share_groups: string[];
  signature_algorithms: string[];
  cipher_suites: string[];
}

export interface PQCDetectionInfo {
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

export interface FlowLog {
  timestamp: string;
  flow_id: number;
  in_iface: string;
  event_type: string;
  src_ip: string;
  src_port: number;
  dest_ip: string;
  dest_port: number;
  ip_v: number;
  proto: string;
  app_proto?: string;
  hostname?: string;
  flow: {
    pkts_toserver: number;
    pkts_toclient: number;
    bytes_toserver: number;
    bytes_toclient: number;
    start: string;
    end: string;
    age: number;
    state: string;
    reason: string;
    alerted: boolean;
    tx_cnt?: number;
  };
  tcp?: {
    tcp_flags: string;
    tcp_flags_ts: string;
    tcp_flags_tc: string;
    syn?: boolean;
    fin?: boolean;
    psh?: boolean;
    ack?: boolean;
    ecn?: boolean;
    cwr?: boolean;
    state: string;
    ts_max_regions: number;
    tc_max_regions: number;
  };
  tls?: {
    version?: string;
    sni?: string;
    cipher_suite?: string;
    ja3?: string | null;
  };
  pqc_detection?: PQCDetectionInfo;
  rawPayload?: any;
}

export type PQCStatus = 'safe' | 'vulnerable' | 'unknown';

export interface ProcessedLog extends FlowLog {
  pqcStatus: PQCStatus;
  pqcReason: string;
}

// Determine PQC status based on protocol and connection characteristics
export function determinePQCStatus(log: FlowLog): { status: PQCStatus; reason: string } {
  // Non-TLS protocols are not applicable for PQC check
  if (log.app_proto !== 'tls') {
    return { 
      status: 'unknown', 
      reason: log.app_proto ? `${log.app_proto.toUpperCase()} protocol - N/A` : 'Non-TLS connection' 
    };
  }

  // Simulate PQC detection based on flow characteristics
  // In a real implementation, this would check cipher suites, key exchange algorithms, etc.
  const totalBytes = log.flow.bytes_toserver + log.flow.bytes_toclient;
  
  // PQC key exchanges are typically larger due to bigger key sizes
  // Kyber-768 handshakes are ~3KB larger than classical ECDH
  if (totalBytes > 8000) {
    return { 
      status: 'safe', 
      reason: 'PQC-compatible key exchange detected (ML-KEM-768)' 
    };
  } else if (totalBytes > 5000) {
    return { 
      status: 'vulnerable', 
      reason: 'Classical TLS 1.3 - ECDHE-P256 (Quantum Vulnerable)' 
    };
  } else {
    return { 
      status: 'vulnerable', 
      reason: 'Legacy TLS - RSA key exchange (Quantum Vulnerable)' 
    };
  }
}

export const sampleLogs: FlowLog[] = [
  {"timestamp":"2026-02-09T14:01:45.504852+0530","flow_id":2018624846320095,"in_iface":"en0","event_type":"flow","src_ip":"9.79.193.64","src_port":53856,"dest_ip":"9.0.0.2","dest_port":53,"ip_v":4,"proto":"UDP","app_proto":"dns","flow":{"pkts_toserver":1,"pkts_toclient":1,"bytes_toserver":94,"bytes_toclient":126,"start":"2026-02-09T13:59:59.273389+0530","end":"2026-02-09T13:59:59.287275+0530","age":0,"state":"established","reason":"shutdown","alerted":false,"tx_cnt":2}},
  {"timestamp":"2026-02-09T14:01:45.504856+0530","flow_id":1793478651106419,"in_iface":"en0","event_type":"flow","src_ip":"9.79.193.64","src_port":61326,"dest_ip":"149.81.39.163","dest_port":443,"ip_v":4,"proto":"TCP","app_proto":"tls","flow":{"pkts_toserver":13,"pkts_toclient":10,"bytes_toserver":3751,"bytes_toclient":5548,"start":"2026-02-09T14:00:46.417576+0530","end":"2026-02-09T14:00:51.255590+0530","age":5,"state":"closed","reason":"shutdown","alerted":false,"tx_cnt":1},"tcp":{"tcp_flags":"db","tcp_flags_ts":"db","tcp_flags_tc":"5b","syn":true,"fin":true,"psh":true,"ack":true,"ecn":true,"cwr":true,"state":"closed","ts_max_regions":1,"tc_max_regions":1}},
  {"timestamp":"2026-02-09T14:01:45.504863+0530","flow_id":1082355002266896,"in_iface":"en0","event_type":"flow","src_ip":"9.79.193.64","src_port":61354,"dest_ip":"52.117.12.181","dest_port":443,"ip_v":4,"proto":"TCP","flow":{"pkts_toserver":1,"pkts_toclient":4,"bytes_toserver":78,"bytes_toclient":296,"start":"2026-02-09T14:01:15.514149+0530","end":"2026-02-09T14:01:23.058371+0530","age":8,"state":"new","reason":"shutdown","alerted":false},"tcp":{"tcp_flags":"d2","tcp_flags_ts":"c2","tcp_flags_tc":"52","syn":true,"ack":true,"ecn":true,"cwr":true,"state":"syn_recv","ts_max_regions":1,"tc_max_regions":1}},
  {"timestamp":"2026-02-09T14:01:45.504869+0530","flow_id":1150729827931486,"in_iface":"en0","event_type":"flow","src_ip":"9.79.193.64","src_port":62236,"dest_ip":"9.0.0.2","dest_port":53,"ip_v":4,"proto":"UDP","app_proto":"dns","flow":{"pkts_toserver":1,"pkts_toclient":1,"bytes_toserver":75,"bytes_toclient":75,"start":"2026-02-09T14:00:12.136853+0530","end":"2026-02-09T14:00:12.185318+0530","age":0,"state":"established","reason":"shutdown","alerted":false,"tx_cnt":2}},
  {"timestamp":"2026-02-09T14:01:45.504873+0530","flow_id":1690370076857809,"in_iface":"en0","event_type":"flow","src_ip":"9.79.193.64","src_port":61333,"dest_ip":"185.199.111.153","dest_port":80,"ip_v":4,"proto":"TCP","app_proto":"http","flow":{"pkts_toserver":6,"pkts_toclient":5,"bytes_toserver":587,"bytes_toclient":996,"start":"2026-02-09T14:00:54.721249+0530","end":"2026-02-09T14:00:55.112936+0530","age":1,"state":"closed","reason":"shutdown","alerted":false,"tx_cnt":1},"tcp":{"tcp_flags":"db","tcp_flags_ts":"db","tcp_flags_tc":"1b","syn":true,"fin":true,"psh":true,"ack":true,"ecn":true,"cwr":true,"state":"closed","ts_max_regions":1,"tc_max_regions":1}},
  {"timestamp":"2026-02-09T14:01:45.504879+0530","flow_id":127038969763669,"in_iface":"en0","event_type":"flow","src_ip":"9.79.193.64","src_port":55133,"dest_ip":"8.8.8.8","dest_port":53,"ip_v":4,"proto":"UDP","app_proto":"dns","flow":{"pkts_toserver":1,"pkts_toclient":1,"bytes_toserver":73,"bytes_toclient":89,"start":"2026-02-09T13:58:48.422794+0530","end":"2026-02-09T13:58:48.471593+0530","age":0,"state":"established","reason":"shutdown","alerted":false,"tx_cnt":2}},
  {"timestamp":"2026-02-09T14:01:45.504884+0530","flow_id":1484149758973789,"in_iface":"en0","event_type":"flow","src_ip":"9.79.193.64","src_port":61361,"dest_ip":"158.176.8.208","dest_port":443,"ip_v":4,"proto":"TCP","app_proto":"tls","flow":{"pkts_toserver":17,"pkts_toclient":10,"bytes_toserver":10356,"bytes_toclient":5548,"start":"2026-02-09T14:01:17.280019+0530","end":"2026-02-09T14:01:22.186506+0530","age":5,"state":"closed","reason":"shutdown","alerted":false,"tx_cnt":1},"tcp":{"tcp_flags":"db","tcp_flags_ts":"db","tcp_flags_tc":"5b","syn":true,"fin":true,"psh":true,"ack":true,"ecn":true,"cwr":true,"state":"closed","ts_max_regions":1,"tc_max_regions":1}},
  {"timestamp":"2026-02-09T14:01:45.504891+0530","flow_id":911642514839551,"in_iface":"en0","event_type":"flow","src_ip":"9.79.193.64","src_port":57679,"dest_ip":"9.0.0.2","dest_port":53,"ip_v":4,"proto":"UDP","app_proto":"dns","flow":{"pkts_toserver":1,"pkts_toclient":1,"bytes_toserver":80,"bytes_toclient":159,"start":"2026-02-09T13:58:59.539938+0530","end":"2026-02-09T13:58:59.593081+0530","age":0,"state":"established","reason":"shutdown","alerted":false,"tx_cnt":2}},
  {"timestamp":"2026-02-09T14:01:45.504895+0530","flow_id":992598029785397,"in_iface":"en0","event_type":"flow","src_ip":"9.79.193.64","src_port":61356,"dest_ip":"150.239.167.61","dest_port":443,"ip_v":4,"proto":"TCP","app_proto":"tls","flow":{"pkts_toserver":20,"pkts_toclient":16,"bytes_toserver":6253,"bytes_toclient":6369,"start":"2026-02-09T14:01:15.689859+0530","end":"2026-02-09T14:01:22.011303+0530","age":7,"state":"closed","reason":"shutdown","alerted":false,"tx_cnt":1},"tcp":{"tcp_flags":"db","tcp_flags_ts":"db","tcp_flags_tc":"5b","syn":true,"fin":true,"psh":true,"ack":true,"ecn":true,"cwr":true,"state":"closed","ts_max_regions":1,"tc_max_regions":1}},
  {"timestamp":"2026-02-09T14:01:45.504901+0530","flow_id":1997634213731293,"in_iface":"en0","event_type":"flow","src_ip":"9.79.193.64","src_port":61375,"dest_ip":"150.239.167.61","dest_port":443,"ip_v":4,"proto":"TCP","app_proto":"tls","flow":{"pkts_toserver":13,"pkts_toclient":11,"bytes_toserver":2921,"bytes_toclient":5291,"start":"2026-02-09T14:01:27.530646+0530","end":"2026-02-09T14:01:32.609631+0530","age":5,"state":"closed","reason":"shutdown","alerted":false,"tx_cnt":1},"tcp":{"tcp_flags":"db","tcp_flags_ts":"db","tcp_flags_tc":"5b","syn":true,"fin":true,"psh":true,"ack":true,"ecn":true,"cwr":true,"state":"closed","ts_max_regions":1,"tc_max_regions":1}},
  {"timestamp":"2026-02-09T14:01:45.504908+0530","flow_id":1273782475906938,"in_iface":"en0","event_type":"flow","src_ip":"9.79.193.64","src_port":60477,"dest_ip":"142.251.12.188","dest_port":5228,"ip_v":4,"proto":"TCP","flow":{"pkts_toserver":4,"pkts_toclient":4,"bytes_toserver":216,"bytes_toclient":264,"start":"2026-02-09T13:58:52.886399+0530","end":"2026-02-09T14:01:08.521553+0530","age":136,"state":"new","reason":"shutdown","alerted":false},"tcp":{"tcp_flags":"00","tcp_flags_ts":"00","tcp_flags_tc":"00","state":"closed","ts_max_regions":1,"tc_max_regions":1}},
  {"timestamp":"2026-02-09T14:01:45.504913+0530","flow_id":757281114317042,"in_iface":"en0","event_type":"flow","src_ip":"9.79.193.64","src_port":54878,"dest_ip":"9.0.0.2","dest_port":53,"ip_v":4,"proto":"UDP","app_proto":"dns","flow":{"pkts_toserver":1,"pkts_toclient":1,"bytes_toserver":87,"bytes_toclient":103,"start":"2026-02-09T14:00:50.176318+0530","end":"2026-02-09T14:00:50.190990+0530","age":0,"state":"established","reason":"shutdown","alerted":false,"tx_cnt":2}}
];

export function processLogs(logs: FlowLog[]): ProcessedLog[] {
  return logs.map(log => {
    const { status, reason } = determinePQCStatus(log);
    return {
      ...log,
      pqcStatus: status,
      pqcReason: reason
    };
  });
}
