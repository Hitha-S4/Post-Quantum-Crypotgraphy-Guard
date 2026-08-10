import { useState, useCallback, useRef } from 'react';
import { ProcessedLog } from '@/data/sampleLogs';

export interface TimelineDataPoint {
  time: string;
  safe: number;
  vulnerable: number;
  unknown: number;
  total: number;
}

const MAX_BUCKETS = 30; // max timeline buckets to keep

function getBucketKey(date: Date): string {
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
}

export function useSessionTimeline() {
  const [timeline, setTimeline] = useState<TimelineDataPoint[]>([]);
  const bucketsRef = useRef<Map<string, { safe: number; vulnerable: number; unknown: number }>>(new Map());

  const addLog = useCallback((log: ProcessedLog) => {
    const now = new Date();
    const key = getBucketKey(now);
    const buckets = bucketsRef.current;

    if (!buckets.has(key)) {
      buckets.set(key, { safe: 0, vulnerable: 0, unknown: 0 });
    }

    const bucket = buckets.get(key)!;
    if (log.pqcStatus === 'safe') bucket.safe++;
    else if (log.pqcStatus === 'vulnerable') bucket.vulnerable++;
    else bucket.unknown++;

    // Trim old buckets
    const keys = Array.from(buckets.keys());
    while (keys.length > MAX_BUCKETS) {
      buckets.delete(keys.shift()!);
    }

    // Convert to array
    const data: TimelineDataPoint[] = Array.from(buckets.entries()).map(([time, counts]) => ({
      time,
      safe: counts.safe,
      vulnerable: counts.vulnerable,
      unknown: counts.unknown,
      total: counts.safe + counts.vulnerable + counts.unknown,
    }));

    setTimeline(data);
  }, []);

  const addLogs = useCallback((logs: ProcessedLog[]) => {
    logs.forEach(log => addLog(log));
  }, [addLog]);

  return { timeline, addLog, addLogs };
}
