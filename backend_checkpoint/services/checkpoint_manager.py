"""
Checkpoint Manager for MiroFish Simulations
Provides automatic checkpointing every N rounds with configurable retention
"""

import os
import json
import shutil
import hashlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class CheckpointMetadata:
    """Metadata for a checkpoint"""
    checkpoint_id: str
    simulation_id: str
    round: int
    timestamp: str
    platforms: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckpointMetadata':
        return cls(
            checkpoint_id=data.get("checkpoint_id", ""),
            simulation_id=data.get("simulation_id", ""),
            round=data.get("round", 0),
            timestamp=data.get("timestamp", ""),
            platforms=data.get("platforms", {}),
            config_snapshot=data.get("config_snapshot", {}),
            metadata=data.get("metadata", {})
        )


class CheckpointManager:
    """
    Manages simulation checkpoints

    Features:
    - Create checkpoints at regular intervals (default: every 5 rounds)
    - Keep last N checkpoints (default: 10)
    - Verify checkpoint integrity via checksums
    - Atomic operations to prevent corruption
    """

    DEFAULT_INTERVAL = 5  # rounds
    DEFAULT_KEEP = 10  # checkpoints to keep

    def __init__(self, simulations_dir: str = None):
        if simulations_dir is None:
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            simulations_dir = os.path.join(backend_dir, "uploads", "simulations")
        self.simulations_dir = simulations_dir

    def _get_simulation_dir(self, simulation_id: str) -> str:
        return os.path.join(self.simulations_dir, simulation_id)

    def _get_checkpoints_dir(self, simulation_id: str) -> str:
        return os.path.join(self._get_simulation_dir(simulation_id), "checkpoints")

    def _calculate_file_hash(self, filepath: str) -> str:
        """Calculate SHA256 hash of a file"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return f"sha256:{sha256.hexdigest()[:16]}"

    def create_checkpoint(
        self,
        simulation_id: str,
        round_num: int,
        platforms: List[str] = None,
        config: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> CheckpointMetadata:
        """Create a checkpoint at the current round"""
        if platforms is None:
            platforms = ["twitter", "reddit"]

        sim_dir = self._get_simulation_dir(simulation_id)
        checkpoints_dir = self._get_checkpoints_dir(simulation_id)
        os.makedirs(checkpoints_dir, exist_ok=True)

        checkpoint_id = f"cp_round_{round_num}"
        checkpoint_dir = os.path.join(checkpoints_dir, checkpoint_id)
        os.makedirs(checkpoint_dir, exist_ok=True)

        platform_data = {}

        for platform in platforms:
            platform_data[platform] = {
                "round": round_num,
                "actions_count": 0,
                "db_size_bytes": 0,
                "db_checksum": None,
                "actions_checksum": None
            }

            # Copy database file
            src_db = os.path.join(sim_dir, f"{platform}_simulation.db")
            if os.path.exists(src_db):
                dst_db = os.path.join(checkpoint_dir, f"{platform}_simulation.db")
                temp_db = f"{dst_db}.tmp"
                shutil.copy2(src_db, temp_db)
                os.rename(temp_db, dst_db)
                platform_data[platform]["db_checksum"] = self._calculate_file_hash(dst_db)
                platform_data[platform]["db_size_bytes"] = os.path.getsize(dst_db)

            # Copy actions log
            src_actions = os.path.join(sim_dir, platform, "actions.jsonl")
            if os.path.exists(src_actions):
                dst_actions = os.path.join(checkpoint_dir, f"{platform}_actions.jsonl")
                with open(src_actions, 'r', encoding='utf-8') as src:
                    with open(dst_actions, 'w', encoding='utf-8') as dst:
                        actions_count = 0
                        for line in src:
                            try:
                                entry = json.loads(line.strip())
                                if entry.get("round", 999) <= round_num:
                                    dst.write(line)
                                    if entry.get("event_type") not in ["simulation_start", "round_start", "round_end"]:
                                        actions_count += 1
                            except json.JSONDecodeError:
                                continue
                        platform_data[platform]["actions_count"] = actions_count
                platform_data[platform]["actions_checksum"] = self._calculate_file_hash(dst_actions)

        checkpoint_metadata = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            simulation_id=simulation_id,
            round=round_num,
            timestamp=datetime.now().isoformat(),
            platforms=platform_data,
            config_snapshot=config or {},
            metadata={
                "checkpoint_type": "auto",
                "reason": metadata.get("reason", "scheduled_checkpoint") if metadata else "scheduled_checkpoint",
                **(metadata or {})
            }
        )

        metadata_path = os.path.join(checkpoint_dir, "metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_metadata.to_dict(), f, ensure_ascii=False, indent=2)

        # Update latest symlink
        latest_link = os.path.join(checkpoints_dir, "latest")
        if os.path.islink(latest_link):
            os.remove(latest_link)
        elif os.path.exists(latest_link):
            shutil.rmtree(latest_link)

        try:
            os.symlink(checkpoint_id, latest_link)
        except (OSError, NotImplementedError):
            shutil.copytree(checkpoint_dir, latest_link, dirs_exist_ok=True)

        self.cleanup_old_checkpoints(simulation_id)
        return checkpoint_metadata

    def list_checkpoints(self, simulation_id: str) -> List[CheckpointMetadata]:
        """List all checkpoints for a simulation"""
        checkpoints_dir = self._get_checkpoints_dir(simulation_id)
        if not os.path.exists(checkpoints_dir):
            return []

        checkpoints = []
        for item in os.listdir(checkpoints_dir):
            if item.startswith("cp_round_"):
                metadata_path = os.path.join(checkpoints_dir, item, "metadata.json")
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        checkpoints.append(CheckpointMetadata.from_dict(data))
                    except (json.JSONDecodeError, KeyError):
                        continue

        checkpoints.sort(key=lambda c: c.round, reverse=True)
        return checkpoints

    def get_checkpoint(self, simulation_id: str, checkpoint_id: str = "latest") -> Optional[CheckpointMetadata]:
        """Get a specific checkpoint"""
        checkpoints_dir = self._get_checkpoints_dir(simulation_id)

        if checkpoint_id == "latest":
            latest_path = os.path.join(checkpoints_dir, "latest")
            if os.path.islink(latest_path):
                checkpoint_id = os.readlink(latest_path)
            elif os.path.isdir(latest_path):
                checkpoint_id = "latest"
            else:
                return None

        metadata_path = os.path.join(checkpoints_dir, checkpoint_id, "metadata.json")
        if not os.path.exists(metadata_path):
            return None

        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return CheckpointMetadata.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def verify_checkpoint(self, simulation_id: str, checkpoint_id: str = "latest") -> Dict[str, Any]:
        """Verify checkpoint integrity"""
        checkpoints_dir = self._get_checkpoints_dir(simulation_id)

        if checkpoint_id == "latest":
            latest_path = os.path.join(checkpoints_dir, "latest")
            if os.path.islink(latest_path):
                checkpoint_id = os.readlink(latest_path)
            elif os.path.isdir(latest_path):
                checkpoint_id = "latest"
            else:
                return {"valid": False, "error": "No latest checkpoint found"}

        checkpoint_dir = os.path.join(checkpoints_dir, checkpoint_id)
        metadata_path = os.path.join(checkpoint_dir, "metadata.json")

        if not os.path.exists(metadata_path):
            return {"valid": False, "error": "Checkpoint metadata not found"}

        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except json.JSONDecodeError:
            return {"valid": False, "error": "Invalid metadata JSON"}

        results = {
            "valid": True,
            "checkpoint_id": checkpoint_id,
            "round": metadata.get("round", 0),
            "platforms": {}
        }

        for platform, platform_meta in metadata.get("platforms", {}).items():
            platform_results = {"valid": True, "errors": []}

            db_path = os.path.join(checkpoint_dir, f"{platform}_simulation.db")
            if os.path.exists(db_path):
                current_hash = self._calculate_file_hash(db_path)
                expected_hash = platform_meta.get("db_checksum")
                if expected_hash and current_hash != expected_hash:
                    platform_results["valid"] = False
                    platform_results["errors"].append("Database checksum mismatch")
            else:
                platform_results["valid"] = False
                platform_results["errors"].append("Database file missing")

            results["platforms"][platform] = platform_results
            if not platform_results["valid"]:
                results["valid"] = False

        return results

    def cleanup_old_checkpoints(self, simulation_id: str, keep: int = None) -> int:
        """Remove old checkpoints, keeping only the last N"""
        if keep is None:
            keep = self.DEFAULT_KEEP

        checkpoints = self.list_checkpoints(simulation_id)
        checkpoints_dir = self._get_checkpoints_dir(simulation_id)

        if len(checkpoints) <= keep:
            return 0

        to_remove = checkpoints[keep:]
        removed_count = 0

        for checkpoint in to_remove:
            checkpoint_path = os.path.join(checkpoints_dir, checkpoint.checkpoint_id)
            try:
                shutil.rmtree(checkpoint_path)
                removed_count += 1
            except (OSError, shutil.Error):
                continue

        return removed_count

    def restore_checkpoint(
        self,
        simulation_id: str,
        checkpoint_id: str = "latest",
        platforms: List[str] = None
    ) -> Dict[str, Any]:
        """Restore simulation state from a checkpoint"""
        if platforms is None:
            platforms = ["twitter", "reddit"]

        checkpoints_dir = self._get_checkpoints_dir(simulation_id)
        sim_dir = self._get_simulation_dir(simulation_id)

        if checkpoint_id == "latest":
            latest_path = os.path.join(checkpoints_dir, "latest")
            if os.path.islink(latest_path):
                checkpoint_id = os.readlink(latest_path)
            elif os.path.isdir(latest_path):
                checkpoint_id = "latest"
            else:
                return {"success": False, "error": "No latest checkpoint found"}

        checkpoint_dir = os.path.join(checkpoints_dir, checkpoint_id)
        if not os.path.exists(checkpoint_dir):
            return {"success": False, "error": f"Checkpoint not found: {checkpoint_id}"}

        verification = self.verify_checkpoint(simulation_id, checkpoint_id)
        if not verification["valid"]:
            return {"success": False, "error": "Checkpoint verification failed", "details": verification}

        results = {
            "success": True,
            "checkpoint_id": checkpoint_id,
            "platforms": {}
        }

        for platform in platforms:
            platform_result = {"success": True}
            src_db = os.path.join(checkpoint_dir, f"{platform}_simulation.db")
            dst_db = os.path.join(sim_dir, f"{platform}_simulation.db")

            if os.path.exists(src_db):
                if os.path.exists(dst_db):
                    backup_db = f"{dst_db}.backup"
                    shutil.copy2(dst_db, backup_db)

                temp_db = f"{dst_db}.tmp"
                shutil.copy2(src_db, temp_db)
                os.rename(temp_db, dst_db)
                platform_result["db_restored"] = True
            else:
                platform_result["db_restored"] = False
                platform_result["error"] = "Database not found in checkpoint"

            results["platforms"][platform] = platform_result

        metadata_path = os.path.join(checkpoint_dir, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                results["metadata"] = json.load(f)

        return results


# Singleton instance
_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """Get or create the CheckpointManager singleton"""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager
