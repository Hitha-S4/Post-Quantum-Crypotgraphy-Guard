import { useState, useEffect, useRef, useMemo } from 'react';
import { PQCStatusBadge } from './PQCStatusBadge';
import { ArrowDown, Pause, Play, Copy, Checkmark, Filter, Maximize } from '@carbon/icons-react';
import { ProcessedLog, PQCStatus } from '@/data/sampleLogs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface LiveLogTableProps {
  logs: ProcessedLog[];
  connected: boolean;
  isPaused: boolean;
  setIsPaused: (paused: boolean) => void;
}

export function LiveLogTable({ logs, connected, isPaused, setIsPaused }: LiveLogTableProps) {
  const [autoScroll, setAutoScroll] = useState(true);
  const [selectedLog, setSelectedLog] = useState<ProcessedLog | null>(null);
  const [copied, setCopied] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [protocolFilter, setProtocolFilter] = useState<string>('all');
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('all');
  const [isFullScreen, setIsFullScreen] = useState(false);
  const tableRef = useRef<HTMLDivElement>(null);

  // Filter logs based on selected filters
  const filteredLogs = useMemo(() => {
    return logs.filter(log => {
      // Skip unknown status logs
      if (log.pqcStatus === 'unknown') return false;
      
      // Apply status filter
      if (statusFilter !== 'all' && log.pqcStatus !== statusFilter) return false;
      
      // Apply protocol filter
      if (protocolFilter !== 'all') {
        const protocol = log.app_proto?.toLowerCase() || log.proto.toLowerCase();
        if (protocol !== protocolFilter) return false;
      }
      
      // Apply event type filter
      if (eventTypeFilter !== 'all' && log.event_type !== eventTypeFilter) return false;
      
      return true;
    });
  }, [logs, statusFilter, protocolFilter, eventTypeFilter]);

  // Get unique protocols for filter dropdown
  const availableProtocols = useMemo(() => {
    const protocols = new Set<string>();
    logs.forEach(log => {
      if (log.pqcStatus !== 'unknown') {
        const protocol = log.app_proto?.toLowerCase() || log.proto.toLowerCase();
        protocols.add(protocol);
      }
    });
    return Array.from(protocols).sort();
  }, [logs]);

  // Get unique event types for filter dropdown
  const availableEventTypes = useMemo(() => {
    const eventTypes = new Set<string>();
    logs.forEach(log => {
      if (log.pqcStatus !== 'unknown' && log.event_type) {
        eventTypes.add(log.event_type);
      }
    });
    return Array.from(eventTypes).sort();
  }, [logs]);

  // Auto-scroll to top on new logs
  useEffect(() => {
    if (autoScroll && tableRef.current) {
      tableRef.current.scrollTop = 0;
    }
  }, [logs, autoScroll]);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  const getHostname = (log: ProcessedLog) => {
    return log.hostname || log.tls?.sni || '-';
  };

  const copyToClipboard = () => {
    if (selectedLog?.rawPayload) {
      navigator.clipboard.writeText(JSON.stringify(selectedLog.rawPayload, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <>
    <div className="carbon-tile flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold">Live Network Flows</h2>
          <span className="text-xs text-muted-foreground">({filteredLogs.length} of {logs.length} entries)</span>
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-success' : 'bg-destructive'}`} title={connected ? 'WebSocket connected' : 'WebSocket disconnected'} />
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsFullScreen(true)}
            className="p-1.5 bg-muted text-muted-foreground hover:bg-secondary transition-colors"
            title="Open full screen view"
          >
            <Maximize size={16} />
          </button>
          {/* Filters */}
          <div className="flex items-center gap-2">
            <Filter size={16} className="text-muted-foreground" />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[130px] h-8 text-xs">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="safe">PQC Safe</SelectItem>
                <SelectItem value="vulnerable">Vulnerable</SelectItem>
              </SelectContent>
            </Select>
            <Select value={protocolFilter} onValueChange={setProtocolFilter}>
              <SelectTrigger className="w-[130px] h-8 text-xs">
                <SelectValue placeholder="Protocol" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Protocols</SelectItem>
                {availableProtocols.map(proto => (
                  <SelectItem key={proto} value={proto}>
                    {proto.toUpperCase()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={eventTypeFilter} onValueChange={setEventTypeFilter}>
              <SelectTrigger className="w-[130px] h-8 text-xs">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Events</SelectItem>
                {availableEventTypes.map(eventType => (
                  <SelectItem key={eventType} value={eventType}>
                    {eventType.charAt(0).toUpperCase() + eventType.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`p-1.5 transition-colors ${autoScroll ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-secondary'}`}
            title={autoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
          >
            <ArrowDown size={16} />
          </button>
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`p-1.5 transition-colors ${isPaused ? 'bg-warning text-warning-foreground' : 'bg-muted text-muted-foreground hover:bg-secondary'}`}
            title={isPaused ? 'Resume' : 'Pause'}
          >
            {isPaused ? <Play size={16} /> : <Pause size={16} />}
          </button>
        </div>
      </div>

      <div ref={tableRef} className="flex-1 overflow-auto carbon-scrollbar">
        <table className="carbon-data-table">
          <thead className="sticky top-0 z-10">
            <tr>
              <th>Time</th>
              <th>Hostname</th>
              <th>Type</th>
              <th>Source</th>
              <th>Destination</th>
              <th>Bytes</th>
              <th>Posture</th>
              <th>PQC Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.map((log, index) => (
                <tr
                  key={`${log.flow_id}-${index}`}
                  className={`cursor-pointer hover:bg-secondary/50 transition-colors ${index === 0 ? 'animate-pulse-glow' : ''}`}
                  onClick={() => setSelectedLog(log)}
                >
                  <td className="text-muted-foreground">{formatTime(log.timestamp)}</td>
                  <td>
                    <span className="text-xs text-muted-foreground truncate max-w-[200px] block" title={getHostname(log)}>
                      {getHostname(log)}
                    </span>
                  </td>
                  <td>
                    <span className="text-xs text-muted-foreground capitalize">
                      {log.event_type}
                    </span>
                  </td>
                <td>
                  <span className="text-foreground">{log.src_ip}</span>
                  <span className="text-muted-foreground">:{log.src_port}</span>
                </td>
                <td>
                  <span className="text-foreground">{log.dest_ip}</span>
                  <span className="text-muted-foreground">:{log.dest_port}</span>
                </td>
                <td className="text-muted-foreground">
                  {formatBytes(log.flow.bytes_toserver + log.flow.bytes_toclient)}
                </td>
                <td>
                  <span className="text-xs text-muted-foreground capitalize">
                    {log.pqc_detection?.posture || '-'}
                  </span>
                </td>
                  <td>
                    <PQCStatusBadge status={log.pqcStatus} />
                  </td>
                </tr>
            ))}
            {filteredLogs.length === 0 && logs.length > 0 && (
              <tr>
                <td colSpan={8} className="text-center text-muted-foreground py-8">
                  No flows match the selected filters
                </td>
              </tr>
            )}
            {logs.length === 0 && (
              <tr>
                <td colSpan={8} className="text-center text-muted-foreground py-8">
                  {connected ? 'Waiting for network flows...' : 'Connecting to WebSocket...'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>

      {/* Details Modal */}
      <Dialog open={!!selectedLog} onOpenChange={() => setSelectedLog(null)}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Flow Details - {selectedLog?.flow_id}</DialogTitle>
            <DialogDescription>
              Complete information about this network flow
            </DialogDescription>
          </DialogHeader>
          
          {selectedLog && (
            <div className="space-y-4">
              {/* Connection Info */}
              <div className="carbon-tile">
                <h3 className="text-sm font-semibold mb-3">Connection Information</h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div><span className="text-muted-foreground">Source:</span> {selectedLog.src_ip}:{selectedLog.src_port}</div>
                  <div><span className="text-muted-foreground">Destination:</span> {selectedLog.dest_ip}:{selectedLog.dest_port}</div>
                  <div><span className="text-muted-foreground">Protocol:</span> {selectedLog.proto}</div>
                  <div><span className="text-muted-foreground">App Protocol:</span> {selectedLog.app_proto || 'N/A'}</div>
                  <div><span className="text-muted-foreground">State:</span> {selectedLog.flow.state}</div>
                  <div><span className="text-muted-foreground">Bytes:</span> {formatBytes(selectedLog.flow.bytes_toserver + selectedLog.flow.bytes_toclient)}</div>
                </div>
              </div>

              {/* TLS Information */}
              {selectedLog.tls && (
                <div className="carbon-tile">
                  <h3 className="text-sm font-semibold mb-3">TLS Information</h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div><span className="text-muted-foreground">Version:</span> {selectedLog.tls.version || 'N/A'}</div>
                    <div><span className="text-muted-foreground">SNI:</span> {selectedLog.tls.sni || 'N/A'}</div>
                    <div><span className="text-muted-foreground">Cipher Suite:</span> {selectedLog.tls.cipher_suite || 'N/A'}</div>
                    <div><span className="text-muted-foreground">JA3:</span> {selectedLog.tls.ja3 || 'N/A'}</div>
                  </div>
                </div>
              )}

              {/* PQC Detection */}
              {selectedLog.pqc_detection && (
                <div className="carbon-tile">
                  <h3 className="text-sm font-semibold mb-3">PQC Detection</h3>
                  <div className="space-y-3 text-sm">
                    <div className="grid grid-cols-2 gap-3">
                      <div><span className="text-muted-foreground">Status:</span> <PQCStatusBadge status={selectedLog.pqcStatus} /></div>
                      <div><span className="text-muted-foreground">Crypto Type:</span> {selectedLog.pqc_detection.crypto_type}</div>
                      <div><span className="text-muted-foreground">Posture:</span> <span className="capitalize">{selectedLog.pqc_detection.posture}</span></div>
                      <div><span className="text-muted-foreground">Has ECH:</span> {selectedLog.pqc_detection.has_ech ? 'Yes' : 'No'}</div>
                      {selectedLog.pqc_detection.confidence !== undefined && (
                        <div><span className="text-muted-foreground">Confidence:</span> {Math.round(selectedLog.pqc_detection.confidence * 100)}%</div>
                      )}
                      {selectedLog.pqc_detection.detection_method && (
                        <div><span className="text-muted-foreground">Method:</span> {selectedLog.pqc_detection.detection_method}</div>
                      )}
                    </div>
                    
                    {selectedLog.pqc_detection.algorithms && (
                      <div className="mt-4">
                        <h4 className="text-xs font-semibold mb-2">Algorithms Detected</h4>
                        <div className="space-y-2">
                          {selectedLog.pqc_detection.algorithms.supported_groups.length > 0 && (
                            <div>
                              <span className="text-muted-foreground text-xs">Supported Groups:</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {selectedLog.pqc_detection.algorithms.supported_groups.map((g, i) => (
                                  <span key={i} className="carbon-tag-protocol text-xs">{g}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {selectedLog.pqc_detection.algorithms.key_share_groups.length > 0 && (
                            <div>
                              <span className="text-muted-foreground text-xs">Key Share Groups:</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {selectedLog.pqc_detection.algorithms.key_share_groups.map((g, i) => (
                                  <span key={i} className="carbon-tag-protocol text-xs">{g}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {selectedLog.pqc_detection.algorithms.signature_algorithms.length > 0 && (
                            <div>
                              <span className="text-muted-foreground text-xs">Signature Algorithms:</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {selectedLog.pqc_detection.algorithms.signature_algorithms.map((g, i) => (
                                  <span key={i} className="carbon-tag-protocol text-xs">{g}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {selectedLog.pqc_detection.algorithms.cipher_suites.length > 0 && (
                            <div>
                              <span className="text-muted-foreground text-xs">Cipher Suites:</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {selectedLog.pqc_detection.algorithms.cipher_suites.map((g, i) => (
                                  <span key={i} className="carbon-tag-protocol text-xs">{g}</span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Raw Payload */}
              <div className="carbon-tile">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold">Raw Payload</h3>
                  <button
                    onClick={copyToClipboard}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                    title="Copy to clipboard"
                  >
                    {copied ? (
                      <>
                        <Checkmark size={14} />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy size={14} />
                        Copy
                      </>
                    )}
                  </button>
                </div>
                <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                  {JSON.stringify(selectedLog.rawPayload, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Full Screen Modal */}
      <Dialog open={isFullScreen} onOpenChange={setIsFullScreen}>
        <DialogContent className="max-w-[98vw] max-h-[98vh] w-full h-full p-0">
          <div className="flex flex-col h-full">
            <DialogHeader className="px-6 py-4 border-b border-border">
              <DialogTitle>Live Network Flows - Full Screen View</DialogTitle>
              <DialogDescription>
                Complete view of all network flows with filtering capabilities
              </DialogDescription>
            </DialogHeader>
            
            <div className="flex-1 overflow-hidden p-6">
              <div className="carbon-tile h-full flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-semibold">Live Network Flows</h2>
                    <span className="text-xs text-muted-foreground">({filteredLogs.length} of {logs.length} entries)</span>
                    <span className={`w-2 h-2 rounded-full ${connected ? 'bg-success' : 'bg-destructive'}`} title={connected ? 'WebSocket connected' : 'WebSocket disconnected'} />
                  </div>
                  <div className="flex items-center gap-3">
                    {/* Filters */}
                    <div className="flex items-center gap-2">
                      <Filter size={16} className="text-muted-foreground" />
                      <Select value={statusFilter} onValueChange={setStatusFilter}>
                        <SelectTrigger className="w-[130px] h-8 text-xs">
                          <SelectValue placeholder="Status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Status</SelectItem>
                          <SelectItem value="safe">PQC Safe</SelectItem>
                          <SelectItem value="vulnerable">Vulnerable</SelectItem>
                        </SelectContent>
                      </Select>
                      <Select value={protocolFilter} onValueChange={setProtocolFilter}>
                        <SelectTrigger className="w-[130px] h-8 text-xs">
                          <SelectValue placeholder="Protocol" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Protocols</SelectItem>
                          {availableProtocols.map(proto => (
                            <SelectItem key={proto} value={proto}>
                              {proto.toUpperCase()}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Select value={eventTypeFilter} onValueChange={setEventTypeFilter}>
                        <SelectTrigger className="w-[130px] h-8 text-xs">
                          <SelectValue placeholder="Type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Events</SelectItem>
                          {availableEventTypes.map(eventType => (
                            <SelectItem key={eventType} value={eventType}>
                              {eventType.charAt(0).toUpperCase() + eventType.slice(1)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <button
                      onClick={() => setAutoScroll(!autoScroll)}
                      className={`p-1.5 transition-colors ${autoScroll ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-secondary'}`}
                      title={autoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
                    >
                      <ArrowDown size={16} />
                    </button>
                    <button
                      onClick={() => setIsPaused(!isPaused)}
                      className={`p-1.5 transition-colors ${isPaused ? 'bg-warning text-warning-foreground' : 'bg-muted text-muted-foreground hover:bg-secondary'}`}
                      title={isPaused ? 'Resume' : 'Pause'}
                    >
                      {isPaused ? <Play size={16} /> : <Pause size={16} />}
                    </button>
                  </div>
                </div>

                <div className="flex-1 overflow-auto carbon-scrollbar">
                  <table className="carbon-data-table">
                    <thead className="sticky top-0 z-10">
                      <tr>
                        <th>Time</th>
                        <th>Hostname</th>
                        <th>Type</th>
                        <th>Source</th>
                        <th>Destination</th>
                        <th>Bytes</th>
                        <th>Posture</th>
                        <th>PQC Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredLogs.map((log, index) => (
                        <tr
                          key={`${log.flow_id}-${index}`}
                          className={`cursor-pointer hover:bg-secondary/50 transition-colors ${index === 0 ? 'animate-pulse-glow' : ''}`}
                          onClick={() => setSelectedLog(log)}
                        >
                          <td className="text-muted-foreground">{formatTime(log.timestamp)}</td>
                          <td>
                            <span className="text-xs text-muted-foreground truncate max-w-[300px] block" title={getHostname(log)}>
                              {getHostname(log)}
                            </span>
                          </td>
                          <td>
                            <span className="text-xs text-muted-foreground capitalize">
                              {log.event_type}
                            </span>
                          </td>
                          <td>
                            <span className="text-foreground">{log.src_ip}</span>
                            <span className="text-muted-foreground">:{log.src_port}</span>
                          </td>
                          <td>
                            <span className="text-foreground">{log.dest_ip}</span>
                            <span className="text-muted-foreground">:{log.dest_port}</span>
                          </td>
                          <td className="text-muted-foreground">
                            {formatBytes(log.flow.bytes_toserver + log.flow.bytes_toclient)}
                          </td>
                          <td>
                            <span className="text-xs text-muted-foreground capitalize">
                              {log.pqc_detection?.posture || '-'}
                            </span>
                          </td>
                          <td>
                            <PQCStatusBadge status={log.pqcStatus} />
                          </td>
                        </tr>
                      ))}
                      {filteredLogs.length === 0 && logs.length > 0 && (
                        <tr>
                          <td colSpan={8} className="text-center text-muted-foreground py-8">
                            No flows match the selected filters
                          </td>
                        </tr>
                      )}
                      {logs.length === 0 && (
                        <tr>
                          <td colSpan={8} className="text-center text-muted-foreground py-8">
                            {connected ? 'Waiting for network flows...' : 'Connecting to WebSocket...'}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
