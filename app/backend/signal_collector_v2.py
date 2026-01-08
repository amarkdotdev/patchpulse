"""Cluster Signal Collector v2 with correlation."""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import ClusterSignalDB, ChangeEventDB, DecisionDB

logger = logging.getLogger(__name__)


class SignalCollectorV2:
    """Enhanced signal collector with correlation."""
    
    def __init__(self, db: Session):
        self.db = db
        self.correlation_window_minutes = int(os.getenv("SIGNAL_CORRELATION_WINDOW", "30"))
    
    def collect_signals(self, namespace: str, kind: str = "pod") -> List[Dict]:
        """Collect signals for a namespace."""
        cutoff = datetime.utcnow() - timedelta(minutes=self.correlation_window_minutes)
        
        signals = self.db.query(ClusterSignalDB).filter(
            ClusterSignalDB.namespace == namespace,
            ClusterSignalDB.kind == kind,
            ClusterSignalDB.timestamp >= cutoff
        ).all()
        
        return [
            {
                "kind": s.kind,
                "namespace": s.namespace,
                "name": s.name,
                "metric": s.metric,
                "value": s.value,
                "timestamp": s.timestamp.isoformat()
            }
            for s in signals
        ]
    
    def detect_unstable_namespace(self, namespace: str) -> Dict:
        """Detect if namespace is unstable (has recent issues)."""
        signals = self.collect_signals(namespace)
        
        # Check for problematic signals
        crashloops = [s for s in signals if s["metric"] == "crash_loop_backoff"]
        restarts = [s for s in signals if s["metric"] == "restart_count" and s.get("value", 0) > 5]
        oom_kills = [s for s in signals if s["metric"] == "oom_kill"]
        
        is_unstable = len(crashloops) > 0 or len(restarts) > 0 or len(oom_kills) > 0
        
        return {
            "namespace": namespace,
            "is_unstable": is_unstable,
            "crashloops": len(crashloops),
            "high_restarts": len(restarts),
            "oom_kills": len(oom_kills),
            "signals_count": len(signals),
            "window_minutes": self.correlation_window_minutes
        }
    
    def correlate_to_change(self, change_event_id: str, namespace: str) -> Dict:
        """Correlate signals to a specific change event."""
        change_event = self.db.query(ChangeEventDB).filter(
            ChangeEventDB.id == change_event_id
        ).first()
        
        if not change_event:
            return {"correlated": False}
        
        # Get signals in the time window around the change
        change_time = change_event.timestamp
        window_start = change_time - timedelta(minutes=self.correlation_window_minutes)
        window_end = change_time + timedelta(minutes=self.correlation_window_minutes)
        
        signals = self.db.query(ClusterSignalDB).filter(
            ClusterSignalDB.namespace == namespace,
            ClusterSignalDB.timestamp >= window_start,
            ClusterSignalDB.timestamp <= window_end
        ).all()
        
        # Check for instability
        instability = self.detect_unstable_namespace(namespace)
        
        return {
            "correlated": True,
            "change_event_id": change_event_id,
            "change_timestamp": change_time.isoformat(),
            "signals_in_window": len(signals),
            "namespace_stability": {
                "is_unstable": instability["is_unstable"],
                "issues": {
                    "crashloops": instability["crashloops"],
                    "high_restarts": instability["high_restarts"],
                    "oom_kills": instability["oom_kills"]
                }
            },
            "risk_boost": 15 if instability["is_unstable"] else 0,
            "evidence": [
                {
                    "metric": s.metric,
                    "value": s.value,
                    "timestamp": s.timestamp.isoformat(),
                    "time_from_change": (s.timestamp - change_time).total_seconds()
                }
                for s in signals[:10]  # Top 10 signals
            ]
        }


def get_namespace_stability(namespace: str, db: Session) -> Dict:
    """Get namespace stability assessment."""
    collector = SignalCollectorV2(db)
    return collector.detect_unstable_namespace(namespace)


def correlate_change_to_signals(change_event_id: str, namespace: str, db: Session) -> Dict:
    """Correlate a change event to cluster signals."""
    collector = SignalCollectorV2(db)
    return collector.correlate_to_change(change_event_id, namespace)



