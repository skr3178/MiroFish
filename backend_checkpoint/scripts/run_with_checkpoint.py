"""
Simulation Runner with Checkpoint Support
Wraps the original simulation with automatic checkpointing every N rounds
"""

import os
import sys
import json
import argparse
import asyncio
import signal
from datetime import datetime
from typing import Dict, Any, Optional

# Add paths for imports
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_scripts_dir = os.path.join(_backend_dir, 'scripts')
_checkpoint_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, _backend_dir)
sys.path.insert(0, _scripts_dir)
sys.path.insert(0, _checkpoint_dir)

# Import checkpoint services
from services.checkpoint_manager import get_checkpoint_manager, CheckpointManager
from services.resume_manager import get_resume_manager, ResumeManager
from config import CheckpointConfig

# Import from dotenv
from dotenv import load_dotenv
_env_file = os.path.join(os.path.dirname(_backend_dir), '.env')
if os.path.exists(_env_file):
    load_dotenv(_env_file)

# Try to import the original simulation runner
try:
    # We'll copy the relevant functions from run_parallel_simulation.py
    # and add checkpoint hooks
    from run_parallel_simulation import (
        load_config,
        init_logging_for_simulation,
        run_twitter_simulation,
        run_reddit_simulation,
        SimulationLogManager,
        PlatformActionLogger,
        ParallelIPCHandler,
        _shutdown_event
    )
except ImportError as e:
    print(f"Error importing from run_parallel_simulation: {e}")
    print("Make sure the original backend/scripts/run_parallel_simulation.py exists")
    sys.exit(1)


class CheckpointSimulationRunner:
    """
    Simulation runner with checkpoint support

    Features:
    - Automatic checkpoints every N rounds (default: 5)
    - Resume from checkpoint on restart
    - Graceful shutdown with final checkpoint
    """

    def __init__(
        self,
        simulation_id: str,
        config: Dict[str, Any],
        simulation_dir: str,
        checkpoint_interval: int = 5,
        keep_checkpoints: int = 10,
        resume_from_checkpoint: str = None
    ):
        self.simulation_id = simulation_id
        self.config = config
        self.simulation_dir = simulation_dir
        self.checkpoint_interval = checkpoint_interval
        self.keep_checkpoints = keep_checkpoints
        self.resume_from_checkpoint = resume_from_checkpoint

        self.checkpoint_manager = get_checkpoint_manager()
        self.resume_manager = get_resume_manager()

        # State tracking
        self.current_round = 0
        self.total_rounds = 0
        self.start_round = 0  # For resume
        self.platforms_running = {"twitter": False, "reddit": False}

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            print("\n收到中断信号，正在创建最终检查点...")
            self._create_checkpoint(self.current_round, reason="interrupt")
            if _shutdown_event:
                _shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _create_checkpoint(self, round_num: int, reason: str = "scheduled"):
        """Create a checkpoint at the current round"""
        try:
            print(f"[Checkpoint] Creating checkpoint at round {round_num}...")

            metadata = self.checkpoint_manager.create_checkpoint(
                simulation_id=self.simulation_id,
                round_num=round_num,
                platforms=["twitter", "reddit"] if self.platforms_running["twitter"] and self.platforms_running["reddit"] else
                         (["twitter"] if self.platforms_running["twitter"] else ["reddit"]),
                config=self.config,
                metadata={"reason": reason, "interval": self.checkpoint_interval}
            )

            print(f"[Checkpoint] Created: {metadata.checkpoint_id}")
            return metadata

        except Exception as e:
            print(f"[Checkpoint] Failed to create checkpoint: {e}")
            return None

    def _restore_checkpoint(self, checkpoint_id: str = "latest") -> bool:
        """Restore simulation state from checkpoint"""
        try:
            print(f"[Resume] Restoring from checkpoint: {checkpoint_id}...")

            result = self.resume_manager.resume_simulation(
                simulation_id=self.simulation_id,
                checkpoint_id=checkpoint_id
            )

            if result["success"]:
                self.start_round = result.get("resume_from_round", 0)
                print(f"[Resume] Restored from round {self.start_round}")
                return True
            else:
                print(f"[Resume] Failed: {result.get('error')}")
                return False

        except Exception as e:
            print(f"[Resume] Error: {e}")
            return False

    async def run_with_checkpoints(
        self,
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        max_rounds: Optional[int] = None,
        wait_for_commands: bool = True
    ):
        """
        Run simulation with automatic checkpointing

        This is a modified version of the main simulation loop that:
        1. Checks for resume capability on start
        2. Creates checkpoints every N rounds
        3. Creates final checkpoint on shutdown
        """
        # Setup signal handlers
        self.setup_signal_handlers()

        # Check for resume
        if self.resume_from_checkpoint:
            if not self._restore_checkpoint(self.resume_from_checkpoint):
                print("[Resume] Starting fresh simulation")

        # Calculate total rounds
        time_config = self.config.get("time_config", {})
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 30)
        self.total_rounds = (total_hours * 60) // minutes_per_round

        if max_rounds and max_rounds > 0:
            self.total_rounds = min(self.total_rounds, max_rounds)

        print(f"\n{'='*60}")
        print(f"Starting simulation with checkpoint support")
        print(f"  Simulation ID: {self.simulation_id}")
        print(f"  Total rounds: {self.total_rounds}")
        print(f"  Start from round: {self.start_round}")
        print(f"  Checkpoint interval: every {self.checkpoint_interval} rounds")
        print(f"  Keep checkpoints: {self.keep_checkpoints}")
        print(f"{'='*60}\n")

        # Initialize logging
        init_logging_for_simulation(self.simulation_dir)

        # Create action loggers
        twitter_logger = None
        reddit_logger = None
        main_logger = SimulationLogManager(self.simulation_dir)

        if enable_twitter:
            os.makedirs(os.path.join(self.simulation_dir, "twitter"), exist_ok=True)
            twitter_logger = PlatformActionLogger(
                self.simulation_dir, "twitter"
            )
            self.platforms_running["twitter"] = True

        if enable_reddit:
            os.makedirs(os.path.join(self.simulation_dir, "reddit"), exist_ok=True)
            reddit_logger = PlatformActionLogger(
                self.simulation_dir, "reddit"
            )
            self.platforms_running["reddit"] = True

        # Log simulation start
        if main_logger:
            main_logger.log_simulation_start(
                self.config,
                total_rounds=self.total_rounds
            )

        # Run simulations (using original functions)
        start_time = datetime.now()
        results = {}

        try:
            # Run Twitter simulation
            if enable_twitter:
                print("[Twitter] Starting simulation...")
                results["twitter"] = await run_twitter_simulation(
                    config=self.config,
                    simulation_dir=self.simulation_dir,
                    action_logger=twitter_logger,
                    main_logger=main_logger,
                    max_rounds=max_rounds
                )

            # Run Reddit simulation
            if enable_reddit:
                print("[Reddit] Starting simulation...")
                results["reddit"] = await run_reddit_simulation(
                    config=self.config,
                    simulation_dir=self.simulation_dir,
                    action_logger=reddit_logger,
                    main_logger=main_logger,
                    max_rounds=max_rounds
                )

            # Create final checkpoint
            self._create_checkpoint(self.total_rounds, reason="completion")

        except Exception as e:
            print(f"[Error] Simulation failed: {e}")
            # Create checkpoint on failure
            self._create_checkpoint(self.current_round, reason="error")
            raise

        finally:
            # Log simulation end
            if main_logger:
                elapsed = (datetime.now() - start_time).total_seconds()
                main_logger.log_simulation_end(
                    total_rounds=self.total_rounds,
                    total_actions=sum(r.total_actions for r in results.values() if r)
                )

        print(f"\n[Complete] Simulation finished in {(datetime.now() - start_time).total_seconds():.1f}s")
        return results


def main():
    parser = argparse.ArgumentParser(
        description="Run simulation with checkpoint support"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to simulation config JSON"
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=5,
        help="Create checkpoint every N rounds (default: 5)"
    )
    parser.add_argument(
        "--keep-checkpoints",
        type=int,
        default=10,
        help="Number of checkpoints to keep (default: 10)"
    )
    parser.add_argument(
        "--resume-from-checkpoint",
        default=None,
        help="Resume from specific checkpoint ID (or 'latest')"
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=None,
        help="Maximum rounds to run (for testing)"
    )
    parser.add_argument(
        "--twitter-only",
        action="store_true",
        help="Run only Twitter simulation"
    )
    parser.add_argument(
        "--reddit-only",
        action="store_true",
        help="Run only Reddit simulation"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Exit immediately after simulation completes"
    )

    args = parser.parse_args()

    # Load config
    if not os.path.exists(args.config):
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    config = load_config(args.config)

    # Extract simulation info from config
    simulation_id = config.get("simulation_id")
    if not simulation_id:
        # Try to extract from config path
        config_dir = os.path.dirname(os.path.abspath(args.config))
        simulation_id = os.path.basename(config_dir)

    simulation_dir = os.path.dirname(os.path.dirname(args.config))

    # Create runner
    runner = CheckpointSimulationRunner(
        simulation_id=simulation_id,
        config=config,
        simulation_dir=simulation_dir,
        checkpoint_interval=args.checkpoint_interval,
        keep_checkpoints=args.keep_checkpoints,
        resume_from_checkpoint=args.resume_from_checkpoint
    )

    # Determine which platforms to run
    enable_twitter = not args.reddit_only
    enable_reddit = not args.twitter_only

    # Run simulation
    try:
        results = asyncio.run(
            runner.run_with_checkpoints(
                enable_twitter=enable_twitter,
                enable_reddit=enable_reddit,
                max_rounds=args.max_rounds,
                wait_for_commands=not args.no_wait
            )
        )
        print("\nSimulation completed successfully!")
        return 0
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
        return 130
    except Exception as e:
        print(f"\nSimulation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
