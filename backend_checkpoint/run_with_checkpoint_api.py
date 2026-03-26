"""
MiroFish Backend with Checkpoint Extension
Entry point that wraps the original Flask app with checkpoint routes

Usage:
    python -m backend_checkpoint.run_with_checkpoint_api

This starts the Flask server with checkpoint routes registered at /api/checkpoint/*
"""

import os
import sys

# Ensure the checkpoint module is in the path
_checkpoint_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_checkpoint_dir)
_backend_dir = os.path.join(_project_root, 'backend')

sys.path.insert(0, _project_root)
sys.path.insert(0, _backend_dir)
sys.path.insert(0, _checkpoint_dir)

# Import and configure the original Flask app
from app import create_app

# Create the Flask app
app = create_app()

# Register the checkpoint extension
from integration import register_checkpoint_extension, init_hindsight_database

register_checkpoint_extension(app, prefix="/api")

# Initialize Hindsight database (optional, only if using Hindsight)
try:
    if os.getenv("HINDSIGHT_HOST") or os.getenv("HINDSIGHT_CONNECTION_STRING"):
        init_hindsight_database()
        print("[Checkpoint Extension] Hindsight database initialized")
except Exception as e:
    print(f"[Checkpoint Extension] Hindsight not initialized: {e}")
    print("[Checkpoint Extension] Checkpoint routes will work, but Hindsight graph features require database setup")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run MiroFish Backend with Checkpoint Extension')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5001, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("MiroFish Backend with Checkpoint Extension")
    print(f"{'='*60}")
    print(f"Server: http://{args.host}:{args.port}")
    print(f"Checkpoint API: http://{args.host}:{args.port}/api/checkpoint/")
    print(f"Hindsight API: http://{args.host}:{args.port}/api/hindsight/")
    print(f"{'='*60}\n")

    app.run(host=args.host, port=args.port, debug=args.debug)
