import { ReactNode } from 'react';

interface StatTileProps {
  value: string | number;
  label: string;
  helper?: string;
  icon?: ReactNode;
  trend?: {
    direction: 'up' | 'down';
    value: string;
    positive?: boolean;
  };
  variant?: 'default' | 'success' | 'warning' | 'danger';
}

export function StatTile({ value, label, helper, icon, trend, variant = 'default' }: StatTileProps) {
  const variantClasses = {
    default: 'border-l-2 border-l-primary',
    success: 'border-l-2 border-l-success',
    warning: 'border-l-2 border-l-warning',
    danger: 'border-l-2 border-l-destructive',
  };

  return (
    <div className={`carbon-stat-tile ${variantClasses[variant]}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="carbon-stat-label">{label}</p>
          <p className="carbon-stat-value mt-1">{value}</p>
          {helper && <p className="carbon-stat-helper">{helper}</p>}
        </div>
        {icon && (
          <div className="text-muted-foreground opacity-50">
            {icon}
          </div>
        )}
      </div>
      {trend && (
        <div className="flex items-center gap-1 mt-2">
          <span className={`text-xs ${trend.positive ? 'text-success' : 'text-destructive'}`}>
            {trend.direction === 'up' ? '↑' : '↓'} {trend.value}
          </span>
          <span className="text-xs text-muted-foreground">vs last hour</span>
        </div>
      )}
    </div>
  );
}
