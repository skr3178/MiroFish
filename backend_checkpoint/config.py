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
    interval_rounds: int = 5  # Checkpoint every N rounds
    keep_last_n: int = 10  # Keep last N checkpoints
    auto_checkpoint: bool = True  # Automatic checkpoints
    on_resume_create_backup: bool = True  # Create backup before resume


    verify_integrity: bool = True  # Verify checkpoint integrity
    on_interrupt_create_backup: bool = True  # Create backup on interruption


    use_temp_directory: bool = True  # Use temporary directory for atomic operations
    storage_backend: str = "postgresql"
    # Connection string for Hindsight
    hindsight_database: str = "mirofish_hindsight"
    # Connection string for local simulations storage
    simulations_dir: Optional[str] = None

    checkpoint_interval: int = 5
    max_checkpoints: int = 10
    checkpoint_keep: int = 10

    # Optional configurations
    enable_graph_memory_update: bool = False  # Update graph memory during simulation (Hindsight integration)


    @classmethod
    def get_config(cls) -> CheckpointConfig:
        """Get checkpoint configuration from environment variables"""
        config = CheckpointConfig()
        config.enabled = os.getenv("CHECKPOINT_ENABLED", "true").lower() == "true"
        config.interval_rounds = int(os.getenv("CHECKPOINT_INTERVAL", "5"))
        config.keep_last_n = int(os.getenv("CHECKPOINT_KEEP", "10"))
        config.auto_checkpoint = os.getenv("CHECKPOINT_AUTO", "true").lower() == "true"
        config.on_resume_create_backup = os.getenv("CHECKPOINT_CREATE_BACKUP", "true").lower() == "true"
        config.on_interrupt_verify_integrity = os.getenv("CHECKPOINT_VERIFY_INTEGRITY", "true").lower() == "true"
        config.on_resume_use_temp_directory = os.getenv("CHECKPOINT_USE_TEMP_DIR", "true").lower() == "true"
        config.storage_backend = os.getenv("CHECKPOINT_STORAGE_BACKEND", "postgresql")

        config.simulations_dir = os.getenv("CHECKPOINT_SIMULATIONS_DIR")
        return config
