"""Cluster state service - manages in-memory cluster state.

This is a placeholder for Phase 4 when WebSocket connections
from daemons will populate real-time cluster state.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ClusterStatus:
    total_machines: int = 0
    online_machines: int = 0
    total_gpus: int = 0
    free_gpus: int = 0
    running_models: list[str] = None

    def __post_init__(self):
        if self.running_models is None:
            self.running_models = []

class ClusterStateService:
    """Manages real-time cluster state in memory.

    TODO: Phase 4 - Implement actual state tracking from daemon WebSocket connections.
    """

    def get_status(self) -> ClusterStatus:
        """Get current cluster status. Returns placeholder data for now."""
        return ClusterStatus()

# Singleton instance
cluster_state = ClusterStateService()
