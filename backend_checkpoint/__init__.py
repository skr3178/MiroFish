"""
MiroFish Backend - Checkpoint Extension

This module provides checkpoint/resume functionality for with Hindsight integration (self-hosted, no rate limits).

Export:
- CheckpointManager
- ResumeManager
- HindsightClient
- HindsightTools
- checkpoint_routes
- CheckpointConfig
"""

from .services.checkpoint_manager import CheckpointManager, get_checkpoint_manager
from .services.resume_manager import ResumeManager, get_resume_manager
from .services.hindsight_client import HindsightClient, get_hindsight_client
from .utils.hindsight_tools import HindsightToolsService, get_hindsight_tools
from .api.checkpoint_routes import checkpoint_bp
from .config import CheckpointConfig

# Version info
__version__ = "0.1.0"
__author__ = "MiroFish Checkpoint Extension"
