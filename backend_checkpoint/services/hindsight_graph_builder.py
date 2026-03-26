"""
Hindsight Graph Builder
Replaces Zep Cloud graph building with local LLM + Hindsight PostgreSQL
No rate limits, self-hosted, better benchmark scores
"""

import os
import json
import uuid
import threading
import time
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict

from .hindsight_client import HindsightClient, get_hindsight_client


@dataclass
class Ontology:
    """Ontology definition for entity and relationship types"""
    entity_types: List[Dict[str, Any]]
    edge_types: List[Dict[str, Any]]
    analysis_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EntityNode:
    """Entity node in the knowledge graph"""
    uuid: str
    name: str
    labels: List[str]
    summary: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GraphBuildResult:
    """Result of graph building"""
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]
    chunks_processed: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# LLM Prompts
ONTOLOGY_PROMPT = """You are an expert knowledge graph ontology designer. Analyze the following text and simulation requirement, then design entity and relationship types suitable for **social media simulation**.

**IMPORTANT: Output ONLY valid JSON, no other text.**

## Core Context

We are building a **social media sentiment simulation system**. In this system:
- Each entity is an "account" or "agent" that can post, comment, like, and share on social media
- Entities influence each other through their interactions
- We simulate how opinions spread through a network

Therefore, **entities must be real actors who can post on social media**:

**CAN be entities**:
- Specific individuals (public figures, experts, ordinary people)
- Companies and their official accounts
- Organizations (universities, NGOs, associations)
- Government agencies
- Media outlets

**CANNOT be entities**:
- Abstract concepts ("public opinion", "emotion")
- Topics ("academic integrity", "education reform")
- Views/attitudes ("supporters", "opponents")

## Output Format

```json
{
    "entity_types": [
        {
            "name": "EntityTypeName",
            "description": "Brief description",
            "attributes": [
                {"name": "attribute_name", "type": "text", "description": "desc"}
            ],
            "examples": ["Example1", "Example2"]
        }
    ],
    "edge_types": [
        {
            "name": "RELATIONSHIP_TYPE",
            "description": "Brief description",
            "source_targets": [{"source": "SourceType", "target": "TargetType"}],
            "attributes": []
        }
    ],
    "analysis_summary": "Brief analysis of the text content"
}
```

## Design Guidelines

### Entity Types (exactly 10)

Include these **fallback types** at the end:
- `Person`: Any individual not matching other types
- `Organization`: Any organization not matching other types

Design **8 specific types** based on the text:
- Identify key roles mentioned
- Each type should have clear boundaries
- Description should explain how it differs from fallback types

### Edge Types (6-10)

Common patterns:
- WORKS_AT, STUDIES_AT, MEMBER_OF, LEADS, KNOWS
- REPORTS_TO, PARTNER_OF, PARENT_OF, SIBLING_OF
- LOCATED_IN, FOUNDED_BY

---

## Input

**Simulation Requirement**:
{simulation_requirement}

**Document Content** (first 3000 chars):
{text_sample}

Output ONLY the JSON:"""


ENTITY_EXTRACTION_PROMPT = """You are an entity and relationship extraction system. Extract entities and relationships from the following text chunk.

**IMPORTANT: Output ONLY valid JSON, no other text.**

## Available Entity Types
{entity_types}

## Available Relationship Types
{edge_types}

## Output Format

```json
{
    "entities": [
        {
            "name": "Entity Name",
            "type": "EntityType",
            "summary": "Brief description of this entity",
            "attributes": {
                "attribute_name": "value"
            }
        }
    ],
    "relationships": [
        {
            "source": "Source Entity Name",
            "target": "Target Entity Name",
            "type": "RELATIONSHIP_TYPE",
            "fact": "Natural language description of the relationship"
        }
    ]
}
```

## Guidelines

1. Extract ALL entities mentioned in the text that match the defined types
2. Use the exact entity type names from the schema
3. For Person entities, include relevant attributes
4. Extract relationships between entities mentioned in the text
5. The "fact" field should be a natural language sentence describing the relationship
6. If no entities found, return empty arrays

---

## Text Chunk:
{text_chunk}

Output ONLY the JSON:"""


class HindsightGraphBuilder:
    """
    Hindsight Graph Builder

    Replaces Zep Cloud graph building with:
    1. LLM-based ontology generation
    2. LLM-based entity/relationship extraction
    3. Direct storage in Hindsight PostgreSQL
    """

    def __init__(
        self,
        hindsight_client: HindsightClient = None,
        llm_api_key: str = None,
        llm_base_url: str = None
    ):
        self.hindsight = hindsight_client or get_hindsight_client()
        self.llm_api_key = llm_api_key or os.getenv("LLM_API_KEY")
        self.llm_base_url = llm_base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self._llm_client = None

    @property
    def llm_client(self):
        """Lazy load LLM client"""
        if self._llm_client is None:
            try:
                from openai import OpenAI
                self._llm_client = OpenAI(
                    api_key=self.llm_api_key,
                    base_url=self.llm_base_url
                )
            except ImportError:
                raise ImportError("openai package required: pip install openai")
        return self._llm_client

    def _call_llm(self, prompt: str, max_tokens: int = 4000) -> str:
        """Call LLM and return response"""
        response = self.llm_client.chat.completions.create(
            model="gpt-4o-mini",  # Use fast, cheap model
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3
        )
        return response.choices[0].message.content

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code blocks"""
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            # Find the JSON content between code blocks
            lines = response.split("\n")
            json_lines = []
            in_code_block = False
            for line in lines:
                if line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    json_lines.append(line)
            response = "\n".join(json_lines)

        # Parse JSON
        return json.loads(response)

    # ==================== Ontology Generation ====================

    def extract_ontology(
        self,
        documents: List[str],
        simulation_requirement: str
    ) -> Ontology:
        """
        Extract ontology from documents using LLM

        Args:
            documents: List of document texts
            simulation_requirement: What the simulation should predict

        Returns:
            Ontology with entity_types and edge_types
        """
        # Combine documents for analysis
        combined_text = "\n\n".join(documents)
        text_sample = combined_text[:3000]  # Limit for LLM

        prompt = ONTOLOGY_PROMPT.format(
            simulation_requirement=simulation_requirement,
            text_sample=text_sample
        )

        response = self._call_llm(prompt, max_tokens=4000)
        result = self._parse_json_response(response)

        return Ontology(
            entity_types=result.get("entity_types", []),
            edge_types=result.get("edge_types", []),
            analysis_summary=result.get("analysis_summary", "")
        )

    # ==================== Graph Building ====================

    def build_graph(
        self,
        documents: List[str],
        ontology: Ontology,
        graph_name: str = "MiroFish Graph",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        batch_size: int = 5,
        progress_callback: Callable[[str, int], None] = None
    ) -> GraphBuildResult:
        """
        Build knowledge graph from documents

        Args:
            documents: List of document texts
            ontology: Ontology definition
            graph_name: Name for the graph
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            batch_size: Number of chunks to process in parallel
            progress_callback: Callback(message, progress_percent)

        Returns:
            GraphBuildResult with graph_id and statistics
        """
        def report(msg: str, progress: int):
            if progress_callback:
                progress_callback(msg, progress)

        # 1. Create graph
        report("Creating Hindsight graph...", 5)
        graph_id = self.hindsight.create_graph(graph_name, {
            "ontology": ontology.to_dict(),
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap
        })

        # 2. Chunk documents
        report("Chunking documents...", 10)
        chunks = self._chunk_documents(documents, chunk_size, chunk_overlap)
        total_chunks = len(chunks)

        # 3. Process chunks and extract entities/relationships
        report(f"Processing {total_chunks} chunks...", 15)

        entity_map = {}  # name -> entity_id
        all_relationships = []

        for i, chunk in enumerate(chunks):
            progress = 15 + int((i / total_chunks) * 70)  # 15-85%

            report(f"Extracting from chunk {i+1}/{total_chunks}...", progress)

            try:
                extraction = self._extract_from_chunk(chunk, ontology)

                # Add entities (deduplicate by name)
                for entity in extraction.get("entities", []):
                    name = entity.get("name", "")
                    if name and name not in entity_map:
                        entity_id = self.hindsight.add_entity(
                            graph_id=graph_id,
                            name=name,
                            entity_type=entity.get("type", "Entity"),
                            summary=entity.get("summary", ""),
                            attributes=entity.get("attributes", {})
                        )
                        entity_map[name] = entity_id

                # Collect relationships
                for rel in extraction.get("relationships", []):
                    all_relationships.append(rel)

            except Exception as e:
                print(f"Warning: Failed to extract from chunk {i+1}: {e}")
                continue

        # 4. Add relationships (after all entities exist)
        report("Building relationships...", 85)

        edge_count = 0
        for rel in all_relationships:
            source_name = rel.get("source")
            target_name = rel.get("target")

            source_id = entity_map.get(source_name)
            target_id = entity_map.get(target_name)

            if source_id and target_id:
                try:
                    self.hindsight.add_relationship(
                        graph_id=graph_id,
                        source_id=source_id,
                        target_id=target_id,
                        relationship_type=rel.get("type", "RELATED_TO"),
                        fact=rel.get("fact", "")
                    )
                    edge_count += 1
                except Exception as e:
                    print(f"Warning: Failed to add relationship: {e}")

        # 5. Get final statistics
        report("Finalizing graph...", 95)

        graph_info = self.hindsight.get_graph_info(graph_id)

        report("Graph building complete!", 100)

        return GraphBuildResult(
            graph_id=graph_id,
            node_count=graph_info.get("node_count", len(entity_map)) if graph_info else len(entity_map),
            edge_count=graph_info.get("edge_count", edge_count) if graph_info else edge_count,
            entity_types=list(set(e.get("type", "Entity") for e in entity_map.values() if isinstance(e, dict))),
            chunks_processed=total_chunks
        )

    def build_graph_async(
        self,
        documents: List[str],
        ontology: Ontology,
        graph_name: str = "MiroFish Graph",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        batch_size: int = 5,
        task_manager: Any = None
    ) -> str:
        """
        Build graph asynchronously with task tracking

        Args:
            documents: List of document texts
            ontology: Ontology definition
            graph_name: Name for the graph
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            batch_size: Number of chunks to process in parallel
            task_manager: TaskManager instance for progress tracking

        Returns:
            Task ID for tracking
        """
        if task_manager is None:
            # Create simple task manager if not provided
            from backend.app.models.task import TaskManager
            task_manager = TaskManager()

        task_id = task_manager.create_task(
            task_type="hindsight_graph_build",
            metadata={
                "graph_name": graph_name,
                "chunk_size": chunk_size,
                "document_count": len(documents)
            }
        )

        def worker():
            try:
                task_manager.update_task(task_id, status="processing", progress=5, message="Starting graph build...")

                def progress_callback(msg: str, progress: int):
                    task_manager.update_task(task_id, progress=progress, message=msg)

                result = self.build_graph(
                    documents=documents,
                    ontology=ontology,
                    graph_name=graph_name,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    batch_size=batch_size,
                    progress_callback=progress_callback
                )

                task_manager.complete_task(task_id, result.to_dict())

            except Exception as e:
                import traceback
                task_manager.fail_task(task_id, f"{str(e)}\n{traceback.format_exc()}")

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()

        return task_id

    # ==================== Entity Retrieval ====================

    def get_entities(
        self,
        graph_id: str,
        entity_types: List[str] = None,
        enrich_with_edges: bool = True,
        limit: int = 500
    ) -> List[EntityNode]:
        """
        Get entities from graph with optional filtering and enrichment

        Args:
            graph_id: Graph ID
            entity_types: Filter to specific entity types (None = all)
            enrich_with_edges: Include related edges and nodes
            limit: Maximum entities to return

        Returns:
            List of EntityNode objects
        """
        entities = self.hindsight.get_entities(graph_id, limit=limit)

        # Filter by type if specified
        if entity_types:
            entities = [e for e in entities if e.get("entity_type") in entity_types]

        # Convert to EntityNode format
        entity_nodes = []
        for e in entities:
            node = EntityNode(
                uuid=e.get("entity_id", ""),
                name=e.get("name", ""),
                labels=["Entity", e.get("entity_type", "Entity")],
                summary=e.get("summary", ""),
                attributes=e.get("attributes", {})
            )
            entity_nodes.append(node)

        # Enrich with edges if requested
        if enrich_with_edges:
            relationships = self.hindsight.get_relationships(graph_id, limit=limit * 2)

            for node in entity_nodes:
                node_id = node.uuid
                for rel in relationships:
                    if rel.get("source_id") == node_id or rel.get("target_id") == node_id:
                        edge_data = {
                            "uuid": rel.get("relationship_id", ""),
                            "name": rel.get("relationship_type", ""),
                            "fact": rel.get("fact", ""),
                            "source_node_name": rel.get("source_name", ""),
                            "target_node_name": rel.get("target_name", "")
                        }
                        node.related_edges.append(edge_data)

                        # Add related node info
                        related_id = rel.get("target_id") if rel.get("source_id") == node_id else rel.get("source_id")
                        related_name = rel.get("target_name") if rel.get("source_id") == node_id else rel.get("source_name")
                        node.related_nodes.append({
                            "uuid": related_id,
                            "name": related_name
                        })

        return entity_nodes

    def get_entities_by_type(
        self,
        graph_id: str,
        entity_type: str
    ) -> List[EntityNode]:
        """Get all entities of a specific type"""
        return self.get_entities(graph_id, entity_types=[entity_type])

    # ==================== Helper Methods ====================

    def _chunk_documents(
        self,
        documents: List[str],
        chunk_size: int,
        chunk_overlap: int
    ) -> List[str]:
        """Split documents into overlapping chunks"""
        chunks = []

        for doc in documents:
            # Split by paragraphs first
            paragraphs = doc.split("\n\n")

            current_chunk = ""
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                if len(current_chunk) + len(para) + 2 <= chunk_size:
                    current_chunk += "\n\n" + para if current_chunk else para
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = para

            if current_chunk:
                chunks.append(current_chunk)

        # Create overlapping chunks
        if chunk_overlap > 0:
            overlapped_chunks = []
            for i, chunk in enumerate(chunks):
                if i > 0:
                    # Add end of previous chunk to start of this one
                    prev_chunk = chunks[i - 1]
                    overlap = prev_chunk[-chunk_overlap:] if len(prev_chunk) > chunk_overlap else prev_chunk
                    chunk = overlap + "\n\n" + chunk
                overlapped_chunks.append(chunk)
            return overlapped_chunks

        return chunks

    def _extract_from_chunk(
        self,
        chunk: str,
        ontology: Ontology
    ) -> Dict[str, Any]:
        """Extract entities and relationships from a text chunk"""
        # Format entity types for prompt
        entity_types_str = "\n".join([
            f"- {et.get('name')}: {et.get('description')}"
            for et in ontology.entity_types
        ])

        # Format edge types for prompt
        edge_types_str = "\n".join([
            f"- {et.get('name')}: {et.get('description')}"
            for et in ontology.edge_types
        ])

        prompt = ENTITY_EXTRACTION_PROMPT.format(
            entity_types=entity_types_str,
            edge_types=edge_types_str,
            text_chunk=chunk[:2000]  # Limit chunk size for LLM
        )

        response = self._call_llm(prompt, max_tokens=2000)

        try:
            return self._parse_json_response(response)
        except json.JSONDecodeError:
            return {"entities": [], "relationships": []}


# Singleton instance
_graph_builder: Optional[HindsightGraphBuilder] = None


def get_graph_builder() -> HindsightGraphBuilder:
    """Get or create the HindsightGraphBuilder singleton"""
    global _graph_builder
    if _graph_builder is None:
        _graph_builder = HindsightGraphBuilder()
    return _graph_builder
