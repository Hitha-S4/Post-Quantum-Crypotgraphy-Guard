import { Security, Settings, Network_3 } from '@carbon/icons-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { NotificationBell } from './NotificationBell';

export function DashboardHeader() {
  const navigate = useNavigate();
  const location = useLocation();
  const isTopologyView = location.pathname === '/topology';

  return (
    <header className="carbon-header justify-between">
      <div className="flex items-center gap-3">
        <Security size={20} className="text-primary" />
        <h1 className="text-sm font-semibold text-foreground">
          TLS PQC Compatibility Monitor
        </h1>
      </div>
      
      <div className="flex items-center gap-2">
        <span className="flex items-center gap-2 text-xs text-muted-foreground mr-4">
          <span className="pulse-live flex items-center gap-2 pl-4">
            <span className="ml-5">Live Monitoring</span>
          </span>
        </span>
        
        <button
          onClick={() => navigate(isTopologyView ? '/' : '/topology')}
          className={`p-2 hover:bg-muted transition-colors ${isTopologyView ? 'bg-muted' : ''}`}
          title={isTopologyView ? 'Back to Dashboard' : 'View Network Topology'}
        >
          <Network_3 size={20} className={isTopologyView ? 'text-primary' : 'text-muted-foreground'} />
        </button>
        <NotificationBell />
        <button className="p-2 hover:bg-muted transition-colors">
          <Settings size={20} className="text-muted-foreground" />
        </button>
      </div>
    </header>
  );
}
