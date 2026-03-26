"""
Hindsight Memory Updater
Replaces Zep Cloud graph memory updater with self-hosted Hindsight
Writes simulation activities to Hindsight instead of Zep
"""

import os
import time
import threading
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from queue import Queue, Empty

from .hindsight_client import HindsightClient, get_hindsight_client


@dataclass
class AgentActivity:
    """Agent activity record"""
    platform: str           # twitter / reddit
    agent_id: int
    agent_name: str
    action_type: str        # CREATE_POST, LIKE_POST, etc.
    action_args: Dict[str, Any]
    round_num: int
    timestamp: str

    def to_episode_text(self) -> str:
        """
        Convert activity to natural language description for Hindsight

        Uses natural language format so Hindsight can process it properly
        """
        action_descriptions = {
            "CREATE_POST": self._describe_create_post,
            "LIKE_POST": self._describe_like_post,
            "DISLIKE_POST": self._describe_dislike_post,
            "REPOST": self._describe_repost,
            "QUOTE_POST": self._describe_quote_post,
            "FOLLOW": self._describe_follow,
            "CREATE_COMMENT": self._describe_create_comment,
            "LIKE_COMMENT": self._describe_like_comment,
            "DISLIKE_COMMENT": self._describe_dislike_comment,
            "SEARCH_POSTS": self._describe_search,
            "SEARCH_USER": self._describe_search_user,
            "MUTE": self._describe_mute,
        }

        describe_func = action_descriptions.get(self.action_type, self._describe_generic)
        description = describe_func()

        return f"{self.agent_name}: {description}"

    def _describe_create_post(self) -> str:
        content = self.action_args.get("content", "")
        if content:
            return f"posted: \"{content}\""
        return "posted a new message"

    def _describe_like_post(self) -> str:
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")

        if post_content and post_author:
            return f"liked {post_author}'s post: \"{post_content}\""
        elif post_content:
            return f"liked a post: \"{post_content}\""
        elif post_author:
            return f"liked {post_author}'s post"
        return "liked a post"

    def _describe_dislike_post(self) -> str:
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")

        if post_content and post_author:
            return f"disliked {post_author}'s post: \"{post_content}\""
        elif post_content:
            return f"disliked a post: \"{post_content}\""
        elif post_author:
            return f"disliked {post_author}'s post"
        return "disliked a post"

    def _describe_repost(self) -> str:
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")

        if original_content and original_author:
            return f"reposted {original_author}'s post: \"{original_content}\""
        elif original_content:
            return f"reposted: \"{original_content}\""
        elif original_author:
            return f"reposted {original_author}'s post"
        return "reposted a message"

    def _describe_quote_post(self) -> str:
        original_content = self.action_args.get("original_content", "")
        original_author = self.action_args.get("original_author_name", "")
        quote_content = self.action_args.get("quote_content", "") or self.action_args.get("content", "")

        base = ""
        if original_content and original_author:
            base = f"quoted {original_author}'s post \"{original_content}\""
        elif original_content:
            base = f"quoted a post \"{original_content}\""
        elif original_author:
            base = f"quoted {original_author}'s post"
        else:
            base = "quoted a post"

        if quote_content:
            base += f" with comment: \"{quote_content}\""
        return base

    def _describe_follow(self) -> str:
        target_user_name = self.action_args.get("target_user_name", "")

        if target_user_name:
            return f"followed user \"{target_user_name}\""
        return "followed a user"

    def _describe_create_comment(self) -> str:
        content = self.action_args.get("content", "")
        post_content = self.action_args.get("post_content", "")
        post_author = self.action_args.get("post_author_name", "")

        if content:
            if post_content and post_author:
                return f"commented on {post_author}'s post \"{post_content}\": \"{content}\""
            elif post_content:
                return f"commented on post \"{post_content}\": \"{content}\""
            elif post_author:
                return f"commented on {post_author}'s post: \"{content}\""
            return f"commented: \"{content}\""
        return "wrote a comment"

    def _describe_like_comment(self) -> str:
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")

        if comment_content and comment_author:
            return f"liked {comment_author}'s comment: \"{comment_content}\""
        elif comment_content:
            return f"liked a comment: \"{comment_content}\""
        elif comment_author:
            return f"liked {comment_author}'s comment"
        return "liked a comment"

    def _describe_dislike_comment(self) -> str:
        comment_content = self.action_args.get("comment_content", "")
        comment_author = self.action_args.get("comment_author_name", "")

        if comment_content and comment_author:
            return f"disliked {comment_author}'s comment: \"{comment_content}\""
        elif comment_content:
            return f"disliked a comment: \"{comment_content}\""
        elif comment_author:
            return f"disliked {comment_author}'s comment"
        return "disliked a comment"

    def _describe_search(self) -> str:
        query = self.action_args.get("query", "")
        if query:
            return f"searched for posts about: \"{query}\""
        return "searched for posts"

    def _describe_search_user(self) -> str:
        query = self.action_args.get("query", "")
        if query:
            return f"searched for user: \"{query}\""
        return "searched for a user"

    def _describe_mute(self) -> str:
        target_user_name = self.action_args.get("target_user_name", "")
        if target_user_name:
            return f"muted user \"{target_user_name}\""
        return "muted a user"

    def _describe_generic(self) -> str:
        return f"performed action: {self.action_type}"


class HindsightMemoryUpdater:
    """
    Hindsight Memory Updater

    Monitors simulation action logs and writes agent activities to Hindsight.
    Groups by platform, batches activities (default 5), and writes to PostgreSQL.

    Unlike Zep, there are no rate limits - all activities are stored immediately.
    """

    # Batch size (send to Hindsight after accumulating this many activities per platform)
    BATCH_SIZE = 5

    # Platform display names
    PLATFORM_DISPLAY_NAMES = {
        'twitter': 'World 1',
        'reddit': 'World 2',
    }

    # Send interval (seconds) - can be 0 since no rate limits
    SEND_INTERVAL = 0.1

    def __init__(self, graph_id: str, hindsight_client: HindsightClient = None):
        """
        Initialize the memory updater

        Args:
            graph_id: Hindsight graph ID
            hindsight_client: Hindsight client (optional, creates new one if not provided)
        """
        self.graph_id = graph_id
        self.hindsight = hindsight_client or get_hindsight_client()

        # Activity queue
        self._activity_queue: Queue = Queue()

        # Platform buffers (each platform accumulates to BATCH_SIZE then sends)
        self._platform_buffers: Dict[str, List[AgentActivity]] = {
            'twitter': [],
            'reddit': [],
        }
        self._buffer_lock = threading.Lock()

        # Control flags
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

        # Statistics
        self._total_activities = 0
        self._total_sent = 0
        self._total_items_sent = 0
        self._failed_count = 0
        self._skipped_count = 0

        print(f"[HindsightMemoryUpdater] Initialized: graph_id={graph_id}, batch_size={self.BATCH_SIZE}")

    def _get_platform_display_name(self, platform: str) -> str:
        """Get display name for platform"""
        return self.PLATFORM_DISPLAY_NAMES.get(platform.lower(), platform)

    def start(self):
        """Start the background worker thread"""
        if self._running:
            return

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"HindsightMemoryUpdater-{self.graph_id[:8]}"
        )
        self._worker_thread.start()
        print(f"[HindsightMemoryUpdater] Started: graph_id={self.graph_id}")

    def stop(self):
        """Stop the background worker thread"""
        self._running = False

        # Flush remaining activities
        self._flush_remaining()

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10)

        print(f"[HindsightMemoryUpdater] Stopped: graph_id={self.graph_id}, "
              f"total_activities={self._total_activities}, "
              f"batches_sent={self._total_sent}, "
              f"items_sent={self._total_items_sent}, "
              f"failed={self._failed_count}, "
              f"skipped={self._skipped_count}")

    def add_activity(self, activity: AgentActivity):
        """
        Add an agent activity to the queue

        All meaningful actions are added:
        - CREATE_POST, CREATE_COMMENT, QUOTE_POST
        - LIKE_POST, DISLIKE_POST, REPOST
        - FOLLOW, MUTE
        - LIKE_COMMENT, DISLIKE_COMMENT
        - SEARCH_POSTS, SEARCH_USER

        Args:
            activity: Agent activity record
        """
        # Skip DO_NOTHING type
        if activity.action_type == "DO_NOTHING":
            self._skipped_count += 1
            return

        self._activity_queue.put(activity)
        self._total_activities += 1

    def add_activity_from_dict(self, data: Dict[str, Any], platform: str):
        """
        Add activity from dictionary data

        Args:
            data: Parsed dictionary from actions.jsonl
            platform: Platform name (twitter/reddit)
        """
        # Skip event-type entries
        if "event_type" in data:
            return

        activity = AgentActivity(
            platform=platform,
            agent_id=data.get("agent_id", 0),
            agent_name=data.get("agent_name", ""),
            action_type=data.get("action_type", ""),
            action_args=data.get("action_args", {}),
            round_num=data.get("round", 0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )

        self.add_activity(activity)

    def _worker_loop(self):
        """Background worker loop - batch activities by platform and send to Hindsight"""
        while self._running or not self._activity_queue.empty():
            try:
                # Try to get activity from queue (1 second timeout)
                try:
                    activity = self._activity_queue.get(timeout=1)

                    # Add activity to platform buffer
                    platform = activity.platform.lower()
                    with self._buffer_lock:
                        if platform not in self._platform_buffers:
                            self._platform_buffers[platform] = []
                        self._platform_buffers[platform].append(activity)

                        # Check if platform reached batch size
                        if len(self._platform_buffers[platform]) >= self.BATCH_SIZE:
                            batch = self._platform_buffers[platform][:self.BATCH_SIZE]
                            self._platform_buffers[platform] = self._platform_buffers[platform][self.BATCH_SIZE:]
                            # Release lock before sending
                            self._send_batch_activities(batch, platform)
                            # Send interval (minimal since no rate limits)
                            time.sleep(self.SEND_INTERVAL)

                except Empty:
                    pass

            except Exception as e:
                print(f"[HindsightMemoryUpdater] Worker loop error: {e}")
                time.sleep(1)

    def _send_batch_activities(self, activities: List[AgentActivity], platform: str):
        """
        Send a batch of activities to Hindsight

        Args:
            activities: List of agent activities
            platform: Platform name
        """
        if not activities:
            return

        try:
            # Combine activities into memory entries
            memories = []
            for activity in activities:
                content = activity.to_episode_text()
                memories.append({
                    "content": content,
                    "agent_name": activity.agent_name,
                    "round_num": activity.round_num,
                    "metadata": {
                        "platform": platform,
                        "action_type": activity.action_type,
                        "agent_id": activity.agent_id,
                        "timestamp": activity.timestamp
                    }
                })

            # Send to Hindsight
            memory_ids = self.hindsight.add_memories_batch(self.graph_id, memories)

            self._total_sent += 1
            self._total_items_sent += len(activities)

            platform_display = self._get_platform_display_name(platform)
            print(f"[HindsightMemoryUpdater] Sent batch to {platform_display}: "
                  f"{len(activities)} activities, memory_ids={len(memory_ids)}")

        except Exception as e:
            self._failed_count += 1
            print(f"[HindsightMemoryUpdater] Failed to send batch: {e}")
            # Re-queue activities on failure (with limit to prevent infinite loop)
            if self._failed_count < 100:
                for activity in activities:
                    self._activity_queue.put(activity)

    def _flush_remaining(self):
        """Flush all remaining activities in buffers"""
        with self._buffer_lock:
            for platform, activities in self._platform_buffers.items():
                if activities:
                    self._send_batch_activities(activities, platform)
            self._platform_buffers = {'twitter': [], 'reddit': []}

    def get_stats(self) -> Dict[str, int]:
        """Get current statistics"""
        return {
            "total_activities": self._total_activities,
            "total_sent": self._total_sent,
            "total_items_sent": self._total_items_sent,
            "failed_count": self._failed_count,
            "skipped_count": self._skipped_count,
            "queue_size": self._activity_queue.qsize()
        }


# Singleton instances by graph_id
_memory_updaters: Dict[str, HindsightMemoryUpdater] = {}


def get_memory_updater(graph_id: str) -> HindsightMemoryUpdater:
    """Get or create a HindsightMemoryUpdater for the given graph_id"""
    if graph_id not in _memory_updaters:
        _memory_updaters[graph_id] = HindsightMemoryUpdater(graph_id)
    return _memory_updaters[graph_id]


def stop_all_memory_updaters():
    """Stop all memory updaters"""
    for updater in _memory_updaters.values():
        updater.stop()
    _memory_updaters.clear()
