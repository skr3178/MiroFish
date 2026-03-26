"""
Flask Integration for Checkpoint Extension
Provides easy integration with the main MiroFish Flask app
"""

import os
import sys
from typing import Optional

# Ensure the checkpoint module is in the path
_checkpoint_dir = os.path.dirname(os.path.abspath(__file__))
if _checkpoint_dir not in sys.path:
    sys.path.insert(0, _checkpoint_dir)


def register_checkpoint_extension(app, prefix: str = "/api"):
    """
    Register checkpoint extension with Flask app

    This adds the following endpoints:
    - {prefix}/checkpoint/check/resume/<sim_id> - Check if resume available
    - {prefix}/checkpoint/resume - Resume simulation
    - {prefix}/checkpoint/checkpoints/<sim_id> - List checkpoints
    - {prefix}/hindsight/graph - Create Hindsight graph
    - {prefix}/hindsight/graph/<graph_id>/search - Search graph
    - {prefix}/checkpoint/ontology/generate - Generate ontology (Hindsight flow)
    - {prefix}/checkpoint/prepare - Build graph with Hindsight
    - {prefix}/checkpoint/start - Start simulation with checkpoints
    - {prefix}/checkpoint/generate_report - Generate report with Hindsight

    Args:
        app: Flask application instance
        prefix: URL prefix for routes (default: "/api")

    Usage:
        from backend_checkpoint.integration import register_checkpoint_extension

        app = Flask(__name__)
        register_checkpoint_extension(app)
    """
    from .api.checkpoint_routes import checkpoint_bp, hindsight_bp
    from .api.hindsight_flow_routes import hindsight_flow_bp

    # Register blueprints with prefix
    app.register_blueprint(checkpoint_bp, url_prefix=f"{prefix}/checkpoint")
    app.register_blueprint(hindsight_bp, url_prefix=f"{prefix}/hindsight")
    app.register_blueprint(hindsight_flow_bp, url_prefix=f"{prefix}/checkpoint")

    print(f"[Checkpoint Extension] Registered routes:")
    print(f"  - {prefix}/checkpoint/check/resume/<sim_id>")
    print(f"  - {prefix}/checkpoint/resume")
    print(f"  - {prefix}/checkpoint/checkpoints/<sim_id>")
    print(f"  - {prefix}/hindsight/graph")
    print(f"  - {prefix}/hindsight/graph/<graph_id>/search")
    print(f"  - {prefix}/checkpoint/ontology/generate")
    print(f"  - {prefix}/checkpoint/prepare")
    print(f"  - {prefix}/checkpoint/start")
    print(f"  - {prefix}/checkpoint/generate_report")


def init_hindsight_database(connection_string: Optional[str] = None):
    """
    Initialize Hindsight database

    This creates the necessary tables if they don't exist.

    Args:
        connection_string: PostgreSQL connection string (optional, uses env vars)

    Usage:
        from backend_checkpoint.integration import init_hindsight_database

        init_hindsight_database()
    """
    from .services.hindsight_client import HindsightClient

    client = HindsightClient(connection_string=connection_string)
    print("[Hindsight] Database initialized successfully")
    return client


def get_checkpoint_status(simulation_id: str) -> dict:
    """
    Get checkpoint status for a simulation

    Args:
        simulation_id: Simulation ID

    Returns:
        Dict with checkpoint status and resume availability
    """
    from .services.resume_manager import get_resume_manager

    manager = get_resume_manager()
    return manager.get_simulation_status(simulation_id)


def create_checkpoint_now(simulation_id: str, round_num: int) -> dict:
    """
    Manually create a checkpoint

    Args:
        simulation_id: Simulation ID
        round_num: Current round number

    Returns:
        Checkpoint metadata
    """
    from .services.checkpoint_manager import get_checkpoint_manager

    manager = get_checkpoint_manager()
    return manager.create_checkpoint(simulation_id, round_num)


# Convenience exports
__all__ = [
    'register_checkpoint_extension',
    'init_hindsight_database',
    'get_checkpoint_status',
    'create_checkpoint_now',
]
