"""
Resume Manager for MiroFish Simulations
Detect and and handle resumption of interrupted simulations
"""

import os
import json
import shutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from .checkpoint_manager import CheckpointManager, CheckpointMetadata


@dataclass
class ResumeInfo:
    """Information about a resumable simulation"""
    simulation_id: str
    checkpoint_id: str
    resume_round: int
    total_rounds: int
    progress_percent: float
    timestamp: str
    platforms: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ResumeManager:
    """
    Manages simulation resume functionality

    Features:
    - Detect interrupted simulations
    - Check for available checkpoints
    - Validate checkpoint integrity
    - Provide resume API
    """

    def __init__(self, simulations_dir: str = None):
        if simulations_dir is None:
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            simulations_dir = os.path.join(backend_dir, "uploads", "simulations")

        self.simulations_dir = simulations_dir
        self.checkpoint_manager = CheckpointManager(simulations_dir)

    def _get_simulation_dir(self, simulation_id: str) -> str:
        return os.path.join(self.simulations_dir, simulation_id)

    def _get_state_file(self, simulation_id: str) -> str:
        return os.path.join(self._get_simulation_dir(simulation_id), "state.json")

    def _get_run_state_file(self, simulation_id: str) -> str:
        return os.path.join(self._get_simulation_dir(simulation_id), "run_state.json")

    def detect_resume_candidate(self, simulation_id: str) -> Optional[ResumeInfo]:
        """
        Detect if a simulation can be resumed

        Checks:
        1. State file exists and shows non-completed status
        2. Checkpoints directory exists with at least one checkpoint
        3. Current round < total rounds (not completed)
        4. Checkpoint integrity is valid

        Args:
            simulation_id: Simulation ID

        Returns:
            ResumeInfo if resumable, None otherwise
        """
        sim_dir = self._get_simulation_dir(simulation_id)
        state_file = self._get_state_file(simulation_id)

        if not os.path.exists(state_file):
            return None

        # Load state
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

        # Check if simulation is incomplete
        status = state.get("status", "")
        if status in ["completed", "failed"]:
            return None

        # Check for checkpoints
        checkpoint = self.checkpoint_manager.get_checkpoint(simulation_id, "latest")
        if not checkpoint:
            return None

        # Verify checkpoint
        verification = self.checkpoint_manager.verify_checkpoint(simulation_id, "latest")
        if not verification.get("valid", True):
            return None

        # Get total rounds from config
        config_file = os.path.join(sim_dir, "simulation_config.json")
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            time_config = config.get("time_config", {})
            total_hours = time_config.get("total_simulation_hours", 72)
            minutes_per_round = time_config.get("minutes_per_round", 60)
            total_rounds = (total_hours * 60) // minutes_per_round
        else:
            total_rounds = 144  # Default

        checkpoint_round = checkpoint.round
        progress_percent = (checkpoint_round / total_rounds) * 100

        return ResumeInfo(
            simulation_id=simulation_id,
            checkpoint_id=checkpoint.checkpoint_id,
            resume_round=checkpoint_round,
            total_rounds=total_rounds,
            progress_percent=round(progress_percent, 1),
            timestamp=checkpoint.timestamp,
            platforms=checkpoint.platforms
        )

    def list_resumable_simulations(self) -> List[Dict[str, Any]]:
        """
        List all simulations that can be resumed

        Returns:
            List of dicts with resume info
        """
        resumable = []

        if not os.path.exists(self.simulations_dir):
            return resumable

        for item in os.listdir(self.simulations_dir):
            if item.startswith("sim_"):
                resume_info = self.detect_resume_candidate(item)
                if resume_info:
                    resumable.append(resume_info.to_dict())

        return resumable

    def resume_simulation(
        self,
        simulation_id: str,
        checkpoint_id: str = "latest",
        start_from_round: int = None
    ) -> Dict[str, Any]:
        """
        Resume a simulation from a checkpoint

        Args:
            simulation_id: Simulation ID
            checkpoint_id: Checkpoint ID to "latest" for most recent
            start_from_round: Override start round (optional, defaults to checkpoint round + 1)

        Returns:
            Dict with resume results
        """
        sim_dir = self._get_simulation_dir(simulation_id)

        # Get checkpoint
        checkpoint = self.checkpoint_manager.get_checkpoint(simulation_id, checkpoint_id)
        if not checkpoint:
            return {"success": False, "error": "Checkpoint not found"}

        # Verify checkpoint
        verification = self.checkpoint_manager.verify_checkpoint(simulation_id, checkpoint_id)
        if not verification["valid"]:
            return {"success": False, "error": "Checkpoint verification failed", "details": verification}

        # Restore checkpoint files
        restore_result = self.checkpoint_manager.restore_checkpoint(
            simulation_id,
            checkpoint_id
        )

        if not restore_result["success"]:
            return {"success": False, "error": "Failed to restore checkpoint", "details": restore_result}

        # Update state file to indicate resuming
        state_file = self._get_state_file(simulation_id)
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            state["status"] = "resuming"
            state["resumed_from_checkpoint"] = checkpoint.checkpoint_id
            state["current_round"] = checkpoint.round
            state["updated_at"] = datetime.now().isoformat()

            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

        # Update run state file if it exists
        run_state_file = self._get_run_state_file(simulation_id)
        if os.path.exists(run_state_file):
            with open(run_state_file, 'r', encoding='utf-8') as f:
                run_state = json.load(f)
                run_state["runner_status"] = "resuming"
                run_state["current_round"] = checkpoint.round
                run_state["resumed_from_checkpoint"] = checkpoint.checkpoint_id
                run_state["updated_at"] = datetime.now().isoformat()

                with open(run_state_file, 'w', encoding='utf-8') as f:
                    json.dump(run_state, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "simulation_id": simulation_id,
            "checkpoint_id": checkpoint.checkpoint_id,
            "resume_from_round": start_from_round or (checkpoint.round + 1),
            "total_rounds": restore_result.get("metadata", {}).get("config_snapshot", {}).get("time_config", {}).get("total_simulation_hours", 72),
            "message": f"Resuming from round {checkpoint.round + 1}"
        }

    def get_simulation_status(self, simulation_id: str) -> Dict[str, Any]:
        """
        Get current simulation status

        Args:
            simulation_id: Simulation ID

        Returns:
            Dict with status info
        """
        state_file = self._get_state_file(simulation_id)
        run_state_file = self._get_run_state_file(simulation_id)

        result = {"simulation_id": simulation_id}

        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                result["state"] = json.load(f)

        if os.path.exists(run_state_file):
            with open(run_state_file, 'r', encoding='utf-8') as f:
                result["run_state"] = json.load(f)

        # Check resume availability
        resume_info = self.detect_resume_candidate(simulation_id)
        if resume_info:
            result["resume_available"] = resume_info.to_dict()
        else:
            result["resume_available"] = None

        # Get checkpoints list
        checkpoints = self.checkpoint_manager.list_checkpoints(simulation_id)
        result["checkpoints"] = [cp.to_dict() for cp in checkpoints]

        return result


# Singleton instance
_resume_manager: Optional[ResumeManager] = None


def get_resume_manager() -> ResumeManager:
    """Get or create the ResumeManager singleton"""
    global _resume_manager
    if _resume_manager is None:
        _resume_manager = ResumeManager()
    return _resume_manager
