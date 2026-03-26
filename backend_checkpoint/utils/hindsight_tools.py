"""
Hindsight Tools for ReportAgent
Provides the same interface as Zep tools but uses self-hosted Hindsight
"""

import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

# Import from the checkpoint extension
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import original Zep tools for reference
try:
    from backend.app.services.zep_tools import (
    ZepToolsService,
    SearchResult,
    NodeInfo,
    EdgeInfo,
    InsightForgeResult,
    PanoramaResult
    AgentInterview
)
    # Import Hindsight client
try:
    from backend_checkpoint.services.hindsight_client import HindsightClient, get_hindsight_client
    from backend_checkpoint.services.checkpoint_manager import CheckpointManager, get_checkpoint_manager
    from backend_checkpoint.config import CheckpointConfig
except ImportError:
 e:
    # Try to import from original backend
    original_backend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath()), 'backend')
    original_utils = os.path.join(original_backend, 'app', 'utils')
    sys.path.insert(0, os.path.abspath(original_backend) + '/app')
    from backend.app.utils.logger import get_logger

    logger = get_logger('mirofish.hindsight_tools')


class HindsightToolsService:
    """
    Hindsight Tools for ReportAgent
    Drop-in replacement for ZepToolsService
    Uses self-hosted Hindsight instead of Zep Cloud
    """

    def __init__(self, graph_id: str = None):
        """
        Initialize Hindsight Tools Service

        Args:
            graph_id: Graph ID (uses Hindsight graph instead of Zep)
        """
        if graph_id is None:
            raise ValueError("graph_id is required for HindsightToolsService")

        self.graph_id = graph_id
        self.client = get_hindsight_client()
        self.checkpoint_manager = CheckpointManager()
        self.config = CheckpointConfig.get_config()

        logger.info(f"HindsightToolsService initialized for graph_id={graph_id}")

    # ==================== Search Methods ====================

    def insight_forge_search(
        self,
        query: str,
        simulation_requirement: str,
        max_sub_queries: int = 5,
        progress_callback: callable = None
    ) -> InsightForgeResult:
        """
        深度洞察检索 (InsightForge)
        Most powerful retrieval - generates sub-queries and multi-strategy retrieval

        Args:
            query: Search query
            simulation_requirement: Simulation requirement context
            max_sub_queries: Maximum number of sub-queries to generate (default: 5)
            progress_callback: Optional progress callback

        Returns:
            InsightForgeResult with search results
        """
        # Generate sub-queries using LLM
        sub_queries = self._generate_sub_queries(query, simulation_requirement)

        if progress_callback:
            progress_callback("generating_sub_queries...", 10)

        try:
            llm_client = LLMClient()
            prompt = f"""Generate {max_sub_queries} sub-queries for the question: "{query}"

Based on the user's simulation requirement:
What aspects of this prediction scenario are most important to focus on?
Think step-by-step:
- What are the key entities involved in the simulation?
- How do their relationships change over time (temporal aspect)
- What are the potential outcomes or risks
- What are the open questions that need to be answered

Generate at most {max_sub_queries} sub-queries (default: 5).
        """

        # Analyze query and sub-queries
        sub_query_list = []
        for i in range(max_sub_queries):
            sub_query = sub_queries[i]
            sub_query_list.append(sub_query)

        return sub_query_list

    def _search_nodes(
        self,
        query: str,
        entity_types: List[str] = None,
        limit: int = 100
    ) -> Dict[str, List[Dict[str, Any]]:
        """
        Search for entities in the graph

        Args:
            query: Search query (optional)
            entity_types: Filter by entity types (default: all types)
            limit: Maximum results (default: 100)

        Returns:
            List of entity dictionaries with name, type, summary, attributes
        """
        results = self.client.search(
            graph_id=self.graph_id,
            query=query,
            strategies=["graph"],
            scope="nodes",
            limit=limit
        )

        entities = []
        for entity_data in results.get("entities", []):
            entity = {
                "id": entity_data.get("entity_id"),
                "name": entity_data.get("name"),
                "type": entity_data.get("entity_type",                "summary": entity_data.get("summary", ""),
                "attributes": entity_data.get("attributes", {}),
            }
            entities.append(entity)

        return entities

    def _get_node_edges(
        self,
        entity_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get node and its edges for an entity

        Args:
            entity_id: Entity ID
            limit: Maximum results (default: 100)

        Returns:
            List of edge dictionaries with source, target, type, fact
        """
        results = self.client.search(
            graph_id=self.graph_id,
            query=entity_id,
            scope="edges",
            limit=limit
        )

        edges = []
        for edge_data in results.get("relationships", []):
            edge = {
                "id": edge_data.get("relationship_id"),
                "source_id": edge_data.get("source_id"),
                "target_id": edge_data.get("target_id"),
                "type": edge_data.get("relationship_type"),
                "fact": edge_data.get("fact"),
                "source_name": edge_data.get("source_name"),
                "target_name": edge_data.get("target_name"),
            }
            edges.append(edge)

        return edges

    def _get_all_nodes(self) -> List[Dict[str, Any]]:
        """Get all nodes in the graph"""
        results = self.client.search(
            graph_id=self.graph_id,
            query="",
            scope="nodes",
            limit=10000
        )

        nodes = []
        for node_data in results.get("nodes", []):
            node = NodeInfo(
                uuid=node_data.get("uuid"),
                name=node_data.get("name"),
                labels=node_data.get("labels", []),
                summary=node_data.get("summary", ""),
                attributes=node_data.get("attributes", {}),
            }
            nodes.append(node)

        return nodes

    def _get_all_edges(self, include_expired: bool = True) -> List[Dict[str, Any]]:
        """
        Get all edges in the graph

        Args:
            include_expired: Whether to include expired/expired relationships

        Returns:
            List of edge dictionaries
        """
        results = self.client.search(
            graph_id=self.graph_id,
            query="",
            scope="edges",
            include_expired=include_expired,
            limit=10000
        )

        edges = []
        for edge_data in results.get("relationships", []):
            edge = EdgeInfo(
                uuid=edge_data.get("uuid"),
                name=edge_data.get("name"),
                fact=edge_data.get("fact"),
                source_node_uuid=edge_data.get("source_node_uuid"),
                target_node_uuid=edge_data.get("target_node_uuid"),
                source_node_name=edge_data.get("source_node_name"),
                target_node_name=edge_data.get("target_node_name"),
                relationship_type=edge_data.get("relationship_type"),
                valid_at=edge_data.get("valid_at"),
                invalid_at=edge_data.get("invalid_at"),
                expired_at=edge_data.get("expired_at"),
                created_at=edge_data.get("created_at"),
            )
            edges.append(edge)

        return edges

    def panorama_search(
        self,
        query: str,
        limit: int = 100
    ) -> PanoramaResult:
        """
        广度搜索 - 获取全貌，包括过期内容

        Args:
            query: Search query
            limit: Maximum results (default: 100)

        Returns:
            PanoramaResult with all nodes and edges (active and historical)
        """
        # Get all nodes and edges
        all_nodes = self._get_all_nodes()
        all_edges = self._get_all_edges(include_expired=True)

        # Separate into active and historical
        active_facts = []
        historical_facts = []

        for node in all_nodes:
            if node.summary:
                active_facts.append(node.summary)

        for edge in all_edges:
            if edge.get("fact") and edge.invalid_at is None:
                active_facts.append(edge.fact)
            elif edge.get("fact"):
                historical_facts.append(edge.fact)

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
            limit: Maximum results (default: 10)

        Returns:
            SearchResult with facts and nodes
        """
        # Quick search using semantic strategy
        results = self.client.search(
            graph_id=self.graph_id,
            query=query,
            strategies=["semantic"],
            limit=limit
        )

        facts = []
        nodes = []

        if "facts" in results.get("strategies", {}).get("semantic", {}).get("facts", []):
            facts.extend(facts)

        if "nodes" in results.get("strategies", {}).get("semantic", {}).get("nodes", []):
            nodes.extend([
                NodeInfo(
                    uuid=node.get("uuid"),
                    name=node.get("name"),
                    labels=node.get("labels", []),
                    summary=node.get("summary", ""),
                    attributes=node.get("attributes", {})
                )
                for node in nodes:
                    nodes.append(NodeInfo(
                        uuid=node.get("uuid"),
                        name=node.get("name"),
                        labels=node.get("labels", []),
                        summary=node.get("summary", ""),
                        attributes=node.get("attributes", {})
                    ))

        return SearchResult(
            query=query,
            facts=facts,
            nodes=nodes,
            total_facts=len(facts),
            total_nodes=len(nodes)
        )

    def get_entity_info(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed entity information

        Args:
            entity_id: Entity ID or
        Returns:
            Entity info dictionary or None
        """
        # Search for entity
        results = self.client.search(
            graph_id=self.graph_id,
            query=entity_id,
            strategies=["graph"],
            limit=1
        )

        entities = results.get("strategies", {}).get("graph", {}).get("entities", [])
        if entities:
            entity_data = entities[0]
            return {
                "id": entity_data.get("entity_id"),
                "name": entity_data.get("name"),
                "type": entity_data.get("entity_type"),
                "summary": entity_data.get("summary", ""),
                "attributes": entity_data.get("attributes", {}),
                "edges": self._get_node_edges(entity_id)
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
        # Search for entity by name
        results = self.client.search(
            graph_id=self.graph_id,
            query=entity_name,
            strategies=["graph"],
            limit=5
        )

        entities = results.get("strategies", {}).get("graph", {}).get("entities", [])
        if entities:
            entity = entities[0]
            return entity.get("summary")

        return None
