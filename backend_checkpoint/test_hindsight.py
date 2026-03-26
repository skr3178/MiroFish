#!/usr/bin/env python3
"""
Quick test script for Hindsight integration
Tests: connection, graph creation, entity/relationship operations, search
"""

import os
import sys

# Setup path
_checkpoint_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _checkpoint_dir)

from services.hindsight_client import HindsightClient


def test_hindsight():
    """Run quick tests for Hindsight"""

    print("=" * 50)
    print("HINDSIGHT INTEGRATION TEST")
    print("=" * 50)

    # Check environment
    print("\n[1/6] Checking environment...")
    host = os.getenv("HINDSIGHT_HOST", "localhost")
    port = os.getenv("HINDSIGHT_PORT", "5432")
    database = os.getenv("HINDSIGHT_DATABASE", "mirofish_hindsight")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Database: {database}")

    # Test connection
    print("\n[2/6] Testing connection...")
    try:
        client = HindsightClient()
        print("  ✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        print("\n  To fix, run:")
        print("    docker run -d --name mirofish-hindsight \\")
        print("      -e POSTGRES_PASSWORD=password \\")
        print("      -e POSTGRES_DB=mirofish_hindsight \\")
        print("      -p 5432:5432 pgvector/pgvector:pg16")
        return False

    # Test graph creation
    print("\n[3/6] Creating test graph...")
    try:
        graph_id = client.create_graph("test_graph", {"purpose": "testing"})
        print(f"  ✓ Graph created: {graph_id}")
    except Exception as e:
        print(f"  ✗ Failed to create graph: {e}")
        return False

    # Test adding entities
    print("\n[4/6] Adding test entities...")
    try:
        entities = [
            {"name": "Alice", "type": "Person", "summary": "A test user"},
            {"name": "Bob", "type": "Person", "summary": "Another test user"},
            {"name": "MiroFish Inc", "type": "Organization", "summary": "A simulation company"}
        ]
        entity_ids = client.add_entities_batch(graph_id, entities)
        print(f"  ✓ Added {len(entity_ids)} entities: {entity_ids}")
    except Exception as e:
        print(f"  ✗ Failed to add entities: {e}")
        return False

    # Test adding relationships
    print("\n[5/6] Adding test relationships...")
    try:
        relationships = [
            {
                "source_id": entity_ids[0],
                "target_id": entity_ids[1],
                "type": "KNOWS",
                "fact": "Alice knows Bob"
            },
            {
                "source_id": entity_ids[0],
                "target_id": entity_ids[2],
                "type": "WORKS_FOR",
                "fact": "Alice works for MiroFish Inc"
            }
        ]
        rel_ids = client.add_relationships_batch(graph_id, relationships)
        print(f"  ✓ Added {len(rel_ids)} relationships: {rel_ids}")
    except Exception as e:
        print(f"  ✗ Failed to add relationships: {e}")
        return False

    # Test search
    print("\n[6/6] Testing search...")
    try:
        results = client.search(graph_id, "Alice", strategies=["semantic", "graph"], limit=5)
        facts = results.get("combined_facts", [])
        entities_found = results.get("strategies", {}).get("graph", {}).get("entities", [])
        print(f"  ✓ Search returned {len(facts)} facts, {len(entities_found)} entities")
        for fact in facts[:3]:
            print(f"    - {fact[:60]}..." if len(fact) > 60 else f"    - {fact}")
    except Exception as e:
        print(f"  ✗ Search failed: {e}")
        return False

    # Cleanup
    print("\n[CLEANUP] Deleting test graph...")
    try:
        client.delete_graph(graph_id)
        print(f"  ✓ Deleted graph: {graph_id}")
    except Exception as e:
        print(f"  ! Could not delete graph: {e}")

    print("\n" + "=" * 50)
    print("ALL TESTS PASSED! ✓")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = test_hindsight()
    sys.exit(0 if success else 1)
