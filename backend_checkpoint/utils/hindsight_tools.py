"""
Hindsight Tools for ReportAgent
Provides the same interface as Zep tools but uses self-hosted Hindsight
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

# Setup path for imports
_checkpoint_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _checkpoint_dir not in sys.path:
    sys.path.insert(0, _checkpoint_dir)

# Configure logger
logger = logging.getLogger('mirofish.hindsight_tools')

# Import Hindsight client
from services.hindsight_client import HindsightClient, get_hindsight_client
from services.checkpoint_manager import CheckpointManager, get_checkpoint_manager
from config import CheckpointConfig


@dataclass
class SearchResult:
    """Search result container"""
    query: str
    facts: List[str] = field(default_factory=list)
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    total_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NodeInfo:
    """Node information"""
    uuid: str
    name: str
    labels: List[str] = field(default_factory=list)
    summary: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EdgeInfo:
    """Edge/relationship information"""
    uuid: str
    name: str
    fact: str = ""
    source_node_uuid: str = ""
    target_node_uuid: str = ""
    source_node_name: str = ""
    target_node_name: str = ""
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class PanoramaResult:
    """Wide-angle search result"""
    query: str
    all_nodes: List[Dict[str, Any]] = field(default_factory=list)
    all_edges: List[Dict[str, Any]] = field(default_factory=list)
    active_facts: List[str] = field(default_factory=list)
    historical_facts: List[str] = field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0
    active_count: int = 0
    historical_count: int = 0


class HindsightToolsService:
    """
    Hindsight Tools for ReportAgent
    Drop-in replacement for ZepToolsService
    Uses self-hosted Hindsight instead of Zep Cloud
    """

    def __init__(self, graph_id: str):
        """
        Initialize Hindsight Tools Service

        Args:
            graph_id: Graph ID (uses Hindsight graph instead of Zep)
        """
        if graph_id is None:
            raise ValueError("graph_id is required for HindsightToolsService")

        self.graph_id = graph_id
        self.client = get_hindsight_client()
        self.checkpoint_manager = get_checkpoint_manager()
        self.config = CheckpointConfig.get_config()

        logger.info(f"HindsightToolsService initialized for graph_id={graph_id}")

    def search_graph(
        self,
        query: str,
        limit: int = 10,
        strategies: List[str] = None
    ) -> SearchResult:
        """
        Search the graph using multiple strategies

        Args:
            query: Search query
            limit: Maximum results
            strategies: Search strategies to use

        Returns:
            SearchResult with facts, nodes, and edges
        """
        if strategies is None:
            strategies = ["semantic", "bm25", "graph"]

        results = self.client.search(
            graph_id=self.graph_id,
            query=query,
            strategies=strategies,
            limit=limit
        )

        facts = []
        nodes = []
        edges = []

        # Extract facts from combined results
        for fact in results.get("combined_facts", []):
            facts.append(fact)

        # Extract nodes from semantic search
        semantic_data = results.get("strategies", {}).get("semantic", {})
        for entity in semantic_data.get("entities", []):
            nodes.append({
                "uuid": entity.get("entity_id", ""),
                "name": entity.get("name", ""),
                "labels": [entity.get("entity_type", "Entity")],
                "summary": entity.get("summary", ""),
                "attributes": entity.get("attributes", {})
            })

        # Extract edges from graph search
        graph_data = results.get("strategies", {}).get("graph", {})
        for rel in graph_data.get("relationships", []):
            edges.append({
                "uuid": rel.get("relationship_id", ""),
                "name": rel.get("relationship_type", ""),
                "fact": rel.get("fact", ""),
                "source_node_uuid": rel.get("source_id", ""),
                "target_node_uuid": rel.get("target_id", ""),
                "source_node_name": rel.get("source_name", ""),
                "target_node_name": rel.get("target_name", "")
            })

        return SearchResult(
            query=query,
            facts=facts,
            nodes=nodes,
            edges=edges,
            total_count=len(facts) + len(nodes) + len(edges)
        )

    def panorama_search(
        self,
        query: str,
        include_expired: bool = True,
        limit: int = 100
    ) -> PanoramaResult:
        """
        Wide-angle search - get all relevant information including expired content

        Args:
            query: Search query
            include_expired: Include expired relationships
            limit: Maximum results

        Returns:
            PanoramaResult with all nodes and edges
        """
        # Get all entities
        entities = self.client.get_entities(self.graph_id, limit=limit)

        # Get all relationships
        relationships = self.client.get_relationships(
            self.graph_id,
            include_expired=include_expired,
            limit=limit
        )

        all_nodes = []
        all_edges = []
        active_facts = []
        historical_facts = []

        for entity in entities:
            all_nodes.append({
                "uuid": entity.get("entity_id", ""),
                "name": entity.get("name", ""),
                "labels": [entity.get("entity_type", "Entity")],
                "summary": entity.get("summary", ""),
                "attributes": entity.get("attributes", {})
            })
            if entity.get("summary"):
                active_facts.append(entity["summary"])

        for rel in relationships:
            all_edges.append({
                "uuid": rel.get("relationship_id", ""),
                "name": rel.get("relationship_type", ""),
                "fact": rel.get("fact", ""),
                "source_node_uuid": rel.get("source_id", ""),
                "target_node_uuid": rel.get("target_id", ""),
                "source_node_name": rel.get("source_name", ""),
                "target_node_name": rel.get("target_name", ""),
                "valid_at": rel.get("valid_at"),
                "invalid_at": rel.get("invalid_at"),
                "expired_at": rel.get("expired_at")
            })
            if rel.get("fact"):
                if rel.get("invalid_at") or rel.get("expired_at"):
                    historical_facts.append(rel["fact"])
                else:
                    active_facts.append(rel["fact"])

        return PanoramaResult(
            query=query,
            all_nodes=all_nodes,
            all_edges=all_edges,
            active_facts=active_facts,
            historical_facts=historical_facts,
            total_nodes=len(all_nodes),
            total_edges=len(all_edges),
            active_count=len(active_facts),
            historical_count=len(historical_facts)
        )

    def quick_search(
        self,
        query: str,
        limit: int = 10
    ) -> SearchResult:
        """
        Quick search - simplified retrieval

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            SearchResult with facts and nodes
        """
        return self.search_graph(query, limit, strategies=["semantic"])

    def get_entity_info(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed entity information

        Args:
            entity_id: Entity ID

        Returns:
            Entity info dictionary or None
        """
        entity = self.client.get_entity(entity_id)
        if entity:
            return {
                "id": entity.get("entity_id", ""),
                "name": entity.get("name", ""),
                "type": entity.get("entity_type", ""),
                "summary": entity.get("summary", ""),
                "attributes": entity.get("attributes", {}),
                "relationships": self.client.get_relationships(
                    self.graph_id,
                    entity_id=entity_id,
                    include_expired=False
                )
            }
        return None

    def get_entity_summary(self, entity_name: str) -> Optional[str]:
        """
        Get entity summary by name

        Args:
            entity_name: Entity name

        Returns:
            Entity summary or None
        """
        results = self.client.search(
            graph_id=self.graph_id,
            query=entity_name,
            strategies=["graph"],
            limit=5
        )

        entities = results.get("strategies", {}).get("graph", {}).get("entities", [])
        if entities:
            return entities[0].get("summary", "")
        return None

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """Get all nodes in the graph"""
        return self.client.get_entities(self.graph_id, limit=10000)

    def get_all_edges(self, include_expired: bool = True) -> List[Dict[str, Any]]:
        """Get all edges in the graph"""
        return self.client.get_relationships(
            self.graph_id,
            include_expired=include_expired,
            limit=10000
        )


# Singleton instance
_hindsight_tools: Optional[HindsightToolsService] = None


def get_hindsight_tools(graph_id: str = None) -> HindsightToolsService:
    """Get or create the HindsightToolsService"""
    if graph_id is None:
        raise ValueError("graph_id is required")
    return HindsightToolsService(graph_id)
