import { Checkmark, Warning, Unknown } from '@carbon/icons-react';
import { PQCStatus } from '@/data/sampleLogs';

interface PQCStatusBadgeProps {
  status: PQCStatus;
  showLabel?: boolean;
}

export function PQCStatusBadge({ status, showLabel = true }: PQCStatusBadgeProps) {
  const config = {
    safe: {
      className: 'carbon-tag-pqc-safe',
      icon: <Checkmark size={12} />,
      label: 'PQC Safe',
    },
    vulnerable: {
      className: 'carbon-tag-pqc-vulnerable',
      icon: <Warning size={12} />,
      label: 'Vulnerable',
    },
    unknown: {
      className: 'carbon-tag-pqc-unknown',
      icon: <Unknown size={12} />,
      label: 'N/A',
    },
  };

  const { className, icon, label } = config[status];

  return (
    <span className={`${className} gap-1`}>
      {icon}
      {showLabel && <span>{label}</span>}
    </span>
  );
}
