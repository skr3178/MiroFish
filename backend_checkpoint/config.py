"""
MiroFish Backend - Checkpoint Extension Configuration
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class CheckpointConfig:
    """Configuration for checkpoint/resume functionality"""
    enabled: bool = True
    interval_rounds: int = 5
    keep_last_n: int = 10
    auto_checkpoint: bool = True
    create_backup_on_resume: bool = True
    verify_integrity: bool = True
    use_temp_directory: bool = True
    storage_backend: str = "postgresql"
    hindsight_database: str = "mirofish_hindsight"
    simulations_dir: Optional[str] = None
    enable_graph_memory_update: bool = False

    @classmethod
    def get_config(cls) -> 'CheckpointConfig':
        """Get checkpoint configuration from environment variables"""
        return cls(
            enabled=os.getenv("CHECKPOINT_ENABLED", "true").lower() == "true",
            interval_rounds=int(os.getenv("CHECKPOINT_INTERVAL", "5")),
            keep_last_n=int(os.getenv("CHECKPOINT_KEEP", "10")),
            auto_checkpoint=os.getenv("CHECKPOINT_AUTO", "true").lower() == "true",
            create_backup_on_resume=os.getenv("CHECKPOINT_CREATE_BACKUP", "true").lower() == "true",
            verify_integrity=os.getenv("CHECKPOINT_VERIFY_INTEGRITY", "true").lower() == "true",
            use_temp_directory=os.getenv("CHECKPOINT_USE_TEMP_DIR", "true").lower() == "true",
            storage_backend=os.getenv("CHECKPOINT_STORAGE_BACKEND", "postgresql"),
            simulations_dir=os.getenv("CHECKPOINT_SIMULATIONS_DIR"),
        )
