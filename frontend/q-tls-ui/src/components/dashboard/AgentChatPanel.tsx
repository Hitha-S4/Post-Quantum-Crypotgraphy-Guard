import { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  Loader2,
  X,
  Maximize2,
  Minimize2,
  Wrench,
  GitBranch,
  ShieldCheck,
  CircleHelp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

interface AgentToolCall {
  tool_name: string;
  purpose: string;
  arguments: Record<string, unknown>;
}

interface AgentEvidenceItem {
  source: string;
  summary: string;
  data: Record<string, unknown>;
}

interface AgentTraceStep {
  node: string;
  status: 'completed' | 'warning' | 'clarification_needed';
  details: Record<string, unknown>;
  timestamp: string;
}

interface AgentVerificationResult {
  grounded: boolean;
  sufficient: boolean;
  issues: string[];
  grounded_tool_names: string[];
}

interface AgentClarificationRequest {
  question: string;
  reason: string;
  options: string[];
}

interface AgentProviderMetadata {
  name: string;
  model: string;
}

interface AgentResponse {
  conversation_id: string;
  query: string;
  status: 'completed' | 'clarification_needed';
  summary: string;
  answer: string;
  risk_level: 'critical' | 'high' | 'medium' | 'low' | 'info';
  confidence: number;
  tool_calls: AgentToolCall[];
  evidence: AgentEvidenceItem[];
  metrics: Record<string, unknown>;
  trace: AgentTraceStep[];
  verification: AgentVerificationResult;
  clarification?: AgentClarificationRequest | null;
  provider?: AgentProviderMetadata | null;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  data?: AgentResponse;
}

interface AgentChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

// Choose which agent to use:
// - 'security-analyst' = Legacy agent (old system)
// - 'orchestrator' = Modern LangGraph multi-agent system (NEW!)
const AGENT_ENDPOINT = 'http://localhost:8000/api/v1/ai/agent/orchestrator';

export const AgentChatPanel = ({ isOpen, onClose }: AgentChatPanelProps) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content:
        "I'm your telemetry-grounded AI Security Analyst. Ask about PQC posture, vulnerable traffic, alerts, topology, or exact counts and I'll plan the investigation, call the right tools, verify grounding, and answer from evidence.",
      timestamp: new Date(),
    },
  ]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    const trimmedInput = input.trim();
    if (!trimmedInput || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: trimmedInput,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(AGENT_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: trimmedInput,
          conversation_id: conversationId,
          time_window_minutes: 60,
          limit: 10,
          include_raw_records: false,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to get response from agent: ${response.status}`);
      }

      const data: AgentResponse = await response.json();
      setConversationId(data.conversation_id);

      const assistantMessage: Message = {
        id: `${Date.now()}-assistant`,
        role: 'assistant',
        content: data.answer || data.summary,
        timestamp: new Date(),
        data,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error calling agent:', error);
      const errorMessage: Message = {
        id: `${Date.now()}-error`,
        role: 'assistant',
        content: 'Sorry, the agent failed while planning or executing the investigation.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk?.toLowerCase()) {
      case 'critical':
        return 'bg-red-500';
      case 'high':
        return 'bg-orange-500';
      case 'medium':
        return 'bg-yellow-500 text-black';
      case 'low':
        return 'bg-blue-500';
      case 'info':
        return 'bg-slate-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getTraceBadgeVariant = (status: AgentTraceStep['status']) => {
    switch (status) {
      case 'completed':
        return 'secondary';
      case 'warning':
        return 'destructive';
      case 'clarification_needed':
        return 'outline';
      default:
        return 'secondary';
    }
  };

  const formatMetricValue = (value: unknown) => {
    if (typeof value === 'number') {
      return Number.isInteger(value) ? value.toString() : value.toFixed(2);
    }
    if (typeof value === 'boolean') {
      return value ? 'true' : 'false';
    }
    if (value === null || value === undefined) {
      return 'n/a';
    }
    return String(value);
  };

  if (!isOpen) return null;

  return (
    <div
      className={`fixed ${
        isExpanded ? 'inset-4' : 'bottom-4 right-4 w-96 h-[700px]'
      } z-50 flex flex-col bg-background border rounded-lg shadow-2xl transition-all duration-300`}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <CardTitle className="text-lg">AI Security Analyst</CardTitle>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-8 w-8"
          >
            {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'assistant' && (
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-lg p-3 ${
                    message.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'
                  }`}
                >
                  <div className="text-sm whitespace-pre-wrap break-words">{message.content}</div>

                  {message.role === 'assistant' && message.data && (
                    <div className="mt-3 space-y-3 border-t pt-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-semibold uppercase tracking-wide opacity-80">
                          Risk
                        </span>
                        <Badge className={getRiskColor(message.data.risk_level)}>
                          {message.data.risk_level.toUpperCase()}
                        </Badge>
                        <Badge variant="outline">
                          Confidence {Math.round(message.data.confidence * 100)}%
                        </Badge>
                        <Badge variant={message.data.verification.grounded ? 'secondary' : 'destructive'}>
                          {message.data.verification.grounded ? 'Grounded' : 'Ungrounded'}
                        </Badge>
                      </div>

                      {message.data.provider && (
                        <div className="text-xs opacity-80">
                          Model: {message.data.provider.name} / {message.data.provider.model}
                        </div>
                      )}

                      {message.data.status === 'clarification_needed' && message.data.clarification && (
                        <div className="space-y-2 rounded-md border border-yellow-500/40 bg-yellow-500/5 p-3">
                          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide">
                            <CircleHelp className="h-3 w-3" />
                            Clarification needed
                          </div>
                          <div className="text-sm font-medium">{message.data.clarification.question}</div>
                          <div className="text-xs opacity-80">{message.data.clarification.reason}</div>
                          {message.data.clarification.options.length > 0 && (
                            <div className="flex flex-wrap gap-1 pt-1">
                              {message.data.clarification.options.map((option, index) => (
                                <Badge key={`${option}-${index}`} variant="outline">
                                  {option}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {Object.keys(message.data.metrics).length > 0 && (
                        <div className="space-y-2">
                          <div className="text-xs font-semibold uppercase tracking-wide opacity-80">
                            Key metrics
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            {Object.entries(message.data.metrics).map(([key, value]) => (
                              <div key={key} className="rounded-md border p-2">
                                <div className="text-[10px] uppercase tracking-wide opacity-70">
                                  {key.split('_').join(' ')}
                                </div>
                                <div className="text-sm font-semibold">{formatMetricValue(value)}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {message.data.tool_calls.length > 0 && (
                        <div className="space-y-1">
                          <div className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide opacity-80">
                            <Wrench className="h-3 w-3" />
                            Tool calls
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {message.data.tool_calls.map((toolCall, index) => (
                              <Badge key={`${toolCall.tool_name}-${index}`} variant="secondary">
                                {toolCall.tool_name}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {message.data.evidence.length > 0 && (
                        <div className="space-y-2">
                          <div className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide opacity-80">
                            <ShieldCheck className="h-3 w-3" />
                            Evidence
                          </div>
                          {message.data.evidence.slice(0, 4).map((evidence, index) => (
                            <div key={`${evidence.source}-${index}`} className="rounded-md border p-2">
                              <div className="text-sm font-medium">{evidence.source}</div>
                              <div className="mt-1 text-xs opacity-90">{evidence.summary}</div>
                            </div>
                          ))}
                        </div>
                      )}

                      {message.data.trace.length > 0 && (
                        <div className="space-y-2">
                          <div className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide opacity-80">
                            <GitBranch className="h-3 w-3" />
                            Execution trace
                          </div>
                          <div className="space-y-2">
                            {message.data.trace.map((step, index) => (
                              <div key={`${step.node}-${index}`} className="rounded-md border p-2">
                                <div className="flex items-center justify-between gap-2">
                                  <div className="text-sm font-medium">{step.node}</div>
                                  <Badge variant={getTraceBadgeVariant(step.status)}>{step.status}</Badge>
                                </div>
                                <div className="mt-1 text-xs opacity-80">
                                  {Object.entries(step.details)
                                    .map(([key, value]) => `${key}: ${formatMetricValue(value)}`)
                                    .join(' • ')}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {message.data.verification.issues.length > 0 && (
                        <div className="space-y-1">
                          <div className="text-xs font-semibold uppercase tracking-wide opacity-80">
                            Verification issues
                          </div>
                          <ul className="list-disc space-y-1 pl-4 text-xs">
                            {message.data.verification.issues.map((issue, index) => (
                              <li key={`${issue}-${index}`}>{issue}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="mt-2 text-xs opacity-60">
                    {message.timestamp.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3 justify-start">
                <div className="flex-shrink-0">
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                </div>
                <div className="bg-muted rounded-lg p-3">
                  <div className="flex items-center gap-2 text-sm">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Planning investigation and gathering telemetry...
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="border-t p-4">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about counts, alerts, PQC posture, or topology..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button onClick={handleSend} disabled={!input.trim() || isLoading} size="icon">
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </CardContent>
    </div>
  );
};

// Made with Bob
