import { useState, useMemo, useCallback, useEffect } from 'react';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { AgentChatButton } from '@/components/dashboard/AgentChatButton';
import { useTopologyData } from '@/hooks/useTopologyData';
import { Renew, Security, WarningAlt, Checkmark } from '@carbon/icons-react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  BackgroundVariant,
  MiniMap,
  useNodesState,
  useEdgesState,
  ConnectionLineType,
  MarkerType,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';

interface NodeData {
  id: string;
  nodeType: 'internal' | 'external';
  secureConnections: number;
  insecureConnections: number;
  connectionCount: number;
  protocols: string[];
  ports: number[];
}

const TopologyView = () => {
  const { data, isLoading, error, refetch } = useTopologyData(60);
  const [selectedNode, setSelectedNode] = useState<NodeData | null>(null);
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [showOnlyPQCSafe, setShowOnlyPQCSafe] = useState(false);

  // Get all available nodes for selection
  const availableNodes = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.nodes).map(([id, nodeData]) => ({
      id,
      label: nodeData.hostname || id,
      type: nodeData.node_type
    }));
  }, [data]);

  // Auto-select first 5 nodes on initial load
  useMemo(() => {
    if (availableNodes.length > 0 && selectedNodeIds.length === 0) {
      setSelectedNodeIds(availableNodes.slice(0, 5).map(n => n.id));
    }
  }, [availableNodes]);

  // Transform API data to React Flow format with performance optimizations
  const { nodes: flowNodes, edges: flowEdges } = useMemo(() => {
    if (!data) return { nodes: [], edges: [] };

    // Create nodes - only for selected nodes
    const nodeEntries = Object.entries(data.nodes).filter(([id]) => selectedNodeIds.includes(id));
    
    // Use hierarchical layout with better spacing to avoid overlapping edges
    const gridCols = Math.ceil(Math.sqrt(nodeEntries.length));
    const horizontalSpacing = 250; // Increased spacing
    const verticalSpacing = 200;   // Increased spacing
    
    const nodes: Node[] = nodeEntries.map(([id, nodeData], index) => {
      const row = Math.floor(index / gridCols);
      const col = index % gridCols;
      
      // Add some randomness to avoid perfect grid alignment
      const offsetX = (Math.random() - 0.5) * 50;
      const offsetY = (Math.random() - 0.5) * 50;
      
      const getNodeColor = () => {
        if (nodeData.node_type === 'internal') return '#3b82f6';
        return nodeData.secure_connections > 0 ? '#22c55e' : '#ef4444';
      };

      return {
        id,
        type: 'default',
        position: {
          x: col * horizontalSpacing + 150 + offsetX,
          y: row * verticalSpacing + 150 + offsetY,
        },
        data: {
          label: id.length > 18 ? (
            id.includes(':')
              ? `${id.split(':')[0]}:...:${id.split(':').pop()}`
              : id.substring(0, 15) + '...'
          ) : id,
          nodeData: {
            nodeType: nodeData.node_type,
            secureConnections: nodeData.secure_connections,
            insecureConnections: nodeData.insecure_connections,
            connectionCount: nodeData.connection_count,
            protocols: nodeData.protocols,
            ports: nodeData.ports,
          },
        },
        style: {
          background: getNodeColor(),
          color: '#ffffff',
          border: '2px solid #ffffff',
          borderRadius: '50%',
          width: 60,
          height: 60,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '10px',
          fontFamily: 'monospace',
          padding: '5px',
          textAlign: 'center',
          cursor: 'grab',
        },
      };
    });

    // Create edges
    const edges: Edge[] = Object.values(data.edges)
      .map(edge => {
        const sourceExists = nodes.find(n => n.id === edge.source_ip);
        const targetExists = nodes.find(n => n.id === edge.destination_ip);
        
        if (!sourceExists || !targetExists) return null;

        const getEdgeColor = () => {
          if (edge.security.is_secure) {
            return edge.security.pqc_status === 'safe' ? '#22c55e' : '#3b82f6';
          }
          return '#ef4444';
        };

        return {
          id: edge.edge_id,
          source: edge.source_ip,
          target: edge.destination_ip,
          type: 'smoothstep',
          animated: true, // Animate all edges to show flow
          style: {
            stroke: getEdgeColor(),
            strokeWidth: Math.min(edge.connection_count * 0.3, 3),
            strokeOpacity: 0.8,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: getEdgeColor(),
            width: 20,
            height: 20,
          },
          data: {
            isSecure: edge.security.is_secure,
            pqcStatus: edge.security.pqc_status,
            connectionCount: edge.connection_count,
            protocol: edge.protocol,
            totalBytes: edge.total_bytes,
          },
        };
      })
      .filter((edge) => edge !== null) as Edge[];

    return { nodes, edges };
  }, [data, selectedNodeIds]);

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  // Update nodes and edges when data changes, but preserve user positions
  useEffect(() => {
    // Only update if node IDs have changed, not on every data refresh
    const currentNodeIds = nodes.map(n => n.id).sort().join(',');
    const newNodeIds = flowNodes.map(n => n.id).sort().join(',');
    
    if (currentNodeIds !== newNodeIds) {
      // Node set changed, update everything
      setNodes(flowNodes);
      setEdges(flowEdges);
    } else if (nodes.length > 0) {
      // Same nodes, just update edges and node data without changing positions
      setNodes(prevNodes =>
        prevNodes.map(node => {
          const newNode = flowNodes.find(n => n.id === node.id);
          return newNode ? { ...newNode, position: node.position } : node;
        })
      );
      setEdges(flowEdges);
    }
  }, [flowNodes, flowEdges]);

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    const nodeData = node.data?.nodeData;
    if (nodeData) {
      setSelectedNode({
        id: node.id,
        ...nodeData,
      });
    }
  }, []);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <DashboardHeader />
      
      <main className="flex-1 p-4 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-foreground">Network Topology</h2>
            <p className="text-xs text-muted-foreground">
              {data && `Showing ${selectedNodeIds.length} of ${data.summary.totalNodes} nodes, ${edges.length} connections · Drag nodes to reposition · Scroll to zoom`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowOnlyPQCSafe(!showOnlyPQCSafe)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs border transition-colors ${
                showOnlyPQCSafe
                  ? 'bg-green-600 text-white border-green-600'
                  : 'bg-muted text-foreground border-border hover:bg-muted/80'
              }`}
              title="Toggle PQC-safe connections only"
            >
              <Security size={14} />
              {showOnlyPQCSafe ? 'PQC Safe Only' : 'All Connections'}
            </button>
            <select
              className="px-3 py-1.5 text-xs bg-muted border border-border rounded text-foreground"
              onChange={(e) => {
                const count = parseInt(e.target.value);
                setSelectedNodeIds(availableNodes.slice(0, count).map(n => n.id));
              }}
              value={selectedNodeIds.length}
            >
              <option value="5">5 nodes</option>
              <option value="10">10 nodes</option>
              <option value="20">20 nodes</option>
              <option value="50">50 nodes</option>
              <option value={availableNodes.length}>All nodes ({availableNodes.length})</option>
            </select>
            <button
              onClick={() => refetch()}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              title="Refresh topology"
            >
              <Renew size={14} className={isLoading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="carbon-tile bg-destructive/10 border-destructive">
            <p className="text-sm text-destructive">Error loading topology: {error.message}</p>
          </div>
        )}

        {isLoading && !data ? (
          <div className="carbon-tile p-8">
            <div className="flex flex-col items-center justify-center space-y-4">
              <Renew size={48} className="animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Loading topology data...</p>
            </div>
          </div>
        ) : (
          <>
        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-4">
          {/* Graph */}
          <div className="lg:col-span-3 carbon-tile p-0 overflow-hidden" style={{ height: '700px' }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              connectionLineType={ConnectionLineType.SmoothStep}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              attributionPosition="bottom-left"
              minZoom={0.1}
              maxZoom={4}
              defaultEdgeOptions={{
                type: 'smoothstep',
                animated: false,
              }}
              proOptions={{ hideAttribution: true }}
              elevateEdgesOnSelect={true}
            >
              <Background
                variant={BackgroundVariant.Dots}
                gap={16}
                size={1}
                color="#27272a"
              />
              <Controls
                className="bg-muted border border-border"
                showInteractive={false}
              />
              <MiniMap
                nodeColor={(node) => {
                  const style = node.style as any;
                  return style?.background || '#3b82f6';
                }}
                className="bg-muted border border-border"
                maskColor="rgba(0, 0, 0, 0.6)"
                pannable
                zoomable
              />
            </ReactFlow>
          </div>

          {/* Info Panel */}
          <div className="space-y-4">
            {/* Legend */}
            <div className="carbon-tile">
              <h3 className="text-sm font-semibold mb-3">Legend</h3>
              <div className="space-y-2 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-[#3b82f6]"></div>
                  <span>Internal Node</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-[#22c55e]"></div>
                  <span>Secure External</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-[#ef4444]"></div>
                  <span>Insecure External</span>
                </div>
                <div className="border-t border-border pt-2 mt-2">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-8 h-0.5 bg-[#22c55e]"></div>
                    <span>PQC Safe</span>
                  </div>
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-8 h-0.5 bg-[#3b82f6]"></div>
                    <span>Secure (Non-PQC)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-0.5 bg-[#ef4444]"></div>
                    <span>Insecure</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Summary Stats */}
            {data && (
              <div className="carbon-tile">
                <h3 className="text-sm font-semibold mb-3">Summary</h3>
                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Total Nodes</span>
                    <span className="font-semibold">{data.summary.totalNodes}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Total Edges</span>
                    <span className="font-semibold">{data.summary.totalEdges}</span>
                  </div>
                  <div className="flex items-center justify-between text-green-600">
                    <span className="flex items-center gap-1">
                      <Checkmark size={12} />
                      Secure
                    </span>
                    <span className="font-semibold">{data.summary.secureConnections}</span>
                  </div>
                  <div className="flex items-center justify-between text-red-600">
                    <span className="flex items-center gap-1">
                      <WarningAlt size={12} />
                      Insecure
                    </span>
                    <span className="font-semibold">{data.summary.insecureConnections}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Selected Node Details */}
            {selectedNode && (
              <div className="carbon-tile">
                <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <Security size={16} />
                  Node Details
                </h3>
                <div className="space-y-2 text-xs">
                  <div>
                    <span className="text-muted-foreground block mb-1">IP Address</span>
                    <span className="font-mono text-[10px] break-all block">{selectedNode.id}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Type</span>
                    <span className="capitalize">{selectedNode.nodeType}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Connections</span>
                    <span>{selectedNode.connectionCount}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-muted-foreground block">Secure</span>
                      <span className="text-green-600 font-semibold">
                        {selectedNode.secureConnections}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">Insecure</span>
                      <span className="text-red-600 font-semibold">
                        {selectedNode.insecureConnections}
                      </span>
                    </div>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Protocols</span>
                    <span>{selectedNode.protocols.join(', ')}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Ports</span>
                    <span className="font-mono text-[10px]">
                      {selectedNode.ports.slice(0, 5).join(', ')}
                      {selectedNode.ports.length > 5 && '...'}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Connections Table - Full Width */}
        <div className="carbon-tile">
          <h3 className="text-sm font-semibold mb-4">Connections Table ({edges.length} connections)</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-border bg-muted/50">
                  <th className="text-left py-3 px-4 text-muted-foreground font-semibold">Source IP</th>
                  <th className="text-left py-3 px-4 text-muted-foreground font-semibold">Destination IP</th>
                  <th className="text-center py-3 px-4 text-muted-foreground font-semibold">Protocol</th>
                  <th className="text-center py-3 px-4 text-muted-foreground font-semibold">Security</th>
                  <th className="text-center py-3 px-4 text-muted-foreground font-semibold">PQC Status</th>
                  <th className="text-center py-3 px-4 text-muted-foreground font-semibold">Connections</th>
                  <th className="text-right py-3 px-4 text-muted-foreground font-semibold">Data Transferred</th>
                </tr>
              </thead>
              <tbody>
                {edges.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-4 text-muted-foreground">
                      No connections to display
                    </td>
                  </tr>
                ) : (
                  edges.map((edge) => (
                    <tr key={edge.id} className="border-b border-border hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4 font-mono text-sm">
                        {edge.source.length > 30 ? edge.source.substring(0, 27) + '...' : edge.source}
                      </td>
                      <td className="py-3 px-4 font-mono text-sm">
                        {edge.target.length > 30 ? edge.target.substring(0, 27) + '...' : edge.target}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="inline-flex items-center px-2 py-1 rounded bg-blue-600/20 text-blue-400 text-xs font-medium">
                          {edge.data?.protocol || 'N/A'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-medium ${
                          edge.data?.isSecure
                            ? 'bg-green-600/20 text-green-400'
                            : 'bg-red-600/20 text-red-400'
                        }`}>
                          {edge.data?.isSecure ? '✓ Secure' : '✗ Insecure'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-medium ${
                          edge.data?.pqcStatus === 'safe'
                            ? 'bg-green-600/20 text-green-400'
                            : edge.data?.pqcStatus === 'vulnerable'
                            ? 'bg-red-600/20 text-red-400'
                            : 'bg-gray-600/20 text-gray-400'
                        }`}>
                          {edge.data?.pqcStatus === 'safe' ? '🔒 PQC Safe' : edge.data?.pqcStatus === 'vulnerable' ? '⚠ Vulnerable' : '? Unknown'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center font-semibold">{edge.data?.connectionCount || 0}</td>
                      <td className="py-3 px-4 text-right font-mono text-sm">
                        {(() => {
                          const bytes = edge.data?.totalBytes || 0;
                          if (bytes < 1024) return `${bytes}B`;
                          if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
                          return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
                        })()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
        </>
        )}
      </main>
      
      {/* AI Agent Chat Button */}
      <AgentChatButton />
    </div>
  );
};

export default TopologyView;

// Made with Bob
