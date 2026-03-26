"""
Checkpoint and Resume API Routes
Provides endpoints for checkpoint management and simulation resumption
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any

from ..services.checkpoint_manager import get_checkpoint_manager
from ..services.resume_manager import get_resume_manager
from ..services.hindsight_client import get_hindsight_client


# Create blueprint
checkpoint_bp = Blueprint('checkpoint', __name__, url_prefix='/api/checkpoint')
hindsight_bp = Blueprint('hindsight', __name__, url_prefix='/api/hindsight')


# ==================== Checkpoint Endpoints ====================

@checkpoint_bp.route('/check/resume/<simulation_id>', methods=['GET'])
def check_resume_available(simulation_id: str):
    """
    Check if a simulation can be resumed

    Returns:
    {
        "success": true,
        "data": {
            "can_resume": true/false,
            "checkpoint_id": "cp_round_20",
            "resume_round": 20,
            "total_rounds": 72,
            "progress_percent": 27.8,
            "timestamp": "2025-03-26T14:30:22",
            "platforms": {...}
        }
    }
    """
    try:
        manager = get_resume_manager()
        resume_info = manager.detect_resume_candidate(simulation_id)

        if resume_info:
            return jsonify({
                "success": True,
                "data": {
                    "can_resume": True,
                    **resume_info.to_dict()
                }
            })
        else:
            return jsonify({
                "success": True,
                "data": {"can_resume": False}
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@checkpoint_bp.route('/resume', methods=['POST'])
def resume_simulation():
    """
    Resume a simulation from checkpoint

    Request body:
    {
        "simulation_id": "sim_xxx",
        "checkpoint_id": "cp_round_20",  // optional, defaults to "latest"
        "start_from_round": 21  // optional, defaults to checkpoint round + 1
    }

    Returns:
    {
        "success": true,
        "data": {
            "simulation_id": "sim_xxx",
            "checkpoint_id": "cp_round_20",
            "resume_from_round": 21,
            "message": "Resuming from round 21"
        }
    }
    """
    try:
        data = request.get_json()
        simulation_id = data.get("simulation_id")
        checkpoint_id = data.get("checkpoint_id", "latest")
        start_from_round = data.get("start_from_round")

        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id required"}), 400

        manager = get_resume_manager()
        result = manager.resume_simulation(
            simulation_id=simulation_id,
            checkpoint_id=checkpoint_id,
            start_from_round=start_from_round
        )

        if result["success"]:
            return jsonify({"success": True, "data": result})
        else:
            return jsonify({"success": False, "error": result.get("error", "Resume failed")}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@checkpoint_bp.route('/checkpoints/<simulation_id>', methods=['GET'])
def list_checkpoints(simulation_id: str):
    """
    List all checkpoints for a simulation

    Returns:
    {
        "success": true,
        "data": [
            {
                "checkpoint_id": "cp_round_20",
                "round": 20,
                "timestamp": "...",
                "platforms": {...}
            },
            ...
        ]
    }
    """
    try:
        manager = get_checkpoint_manager()
        checkpoints = manager.list_checkpoints(simulation_id)

        return jsonify({
            "success": True,
            "data": [cp.to_dict() for cp in checkpoints]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@checkpoint_bp.route('/status/<simulation_id>', methods=['GET'])
def get_simulation_status(simulation_id: str):
    """
    Get simulation status including resume availability

    Returns:
    {
        "success": true,
        "data": {
            "simulation_id": "sim_xxx",
            "state": {...},
            "run_state": {...},
            "resume_available": {...},
            "checkpoints": [...]
        }
    }
    """
    try:
        manager = get_resume_manager()
        status = manager.get_simulation_status(simulation_id)

        return jsonify({"success": True, "data": status})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== Hindsight Endpoints ====================

@hindsight_bp.route('/graph', methods=['POST'])
def create_hindsight_graph():
    """
    Create a new Hindsight graph

    Request body:
    {
        "name": "My Graph",
        "metadata": {...}  // optional
    }

    Returns:
    {
        "success": true,
        "data": {
            "graph_id": "mirofish_xxx"
        }
    }
    """
    try:
        data = request.get_json()
        name = data.get("name", "MiroFish Graph")
        metadata = data.get("metadata")

        client = get_hindsight_client()
        graph_id = client.create_graph(name, metadata)

        return jsonify({
            "success": True,
            "data": {"graph_id": graph_id}
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hindsight_bp.route('/graph/<graph_id>/info', methods=['GET'])
def get_graph_info(graph_id: str):
    """
    Get graph information

    Returns:
    {
        "success": true,
        "data": {
            "graph_id": "...",
            "name": "...",
            "node_count": 50,
            "edge_count": 100,
            ...
        }
    }
    """
    try:
        client = get_hindsight_client()
        info = client.get_graph_info(graph_id)

        if info:
            return jsonify({"success": True, "data": info})
        else:
            return jsonify({"success": False, "error": "Graph not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hindsight_bp.route('/graph/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id: str):
    """
    Delete a graph

    Returns:
    {
        "success": true,
        "message": "Graph deleted"
    }
    """
    try:
        client = get_hindsight_client()
        success = client.delete_graph(graph_id)

        if success:
            return jsonify({"success": True, "message": "Graph deleted"})
        else:
            return jsonify({"success": False, "error": "Graph not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hindsight_bp.route('/graph/<graph_id>/entities', methods=['GET'])
def get_entities(graph_id: str):
    """
    Get entities from a graph

    Query params:
        - entity_type: Filter by entity type (optional)
        - limit: Max results (default: 100)

    Returns:
    {
        "success": true,
        "data": [
            {"entity_id": "...", "name": "...", "entity_type": "...", ...},
            ...
        ]
    }
    """
    try:
        entity_type = request.args.get("entity_type")
        limit = int(request.args.get("limit", 100))

        client = get_hindsight_client()
        entities = client.get_entities(graph_id, entity_type, limit)

        return jsonify({"success": True, "data": entities})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hindsight_bp.route('/graph/<graph_id>/entities', methods=['POST'])
def add_entities(graph_id: str):
    """
    Add entities to a graph

    Request body:
    {
        "entities": [
            {"name": "Alice", "type": "Person", "summary": "...", "attributes": {...}},
            ...
        ]
    }

    Returns:
    {
        "success": true,
        "data": {
            "entity_ids": ["ent_xxx", "ent_yyy", ...]
        }
    }
    """
    try:
        data = request.get_json()
        entities = data.get("entities", [])

        if not entities:
            return jsonify({"success": False, "error": "entities required"}), 400

        client = get_hindsight_client()
        entity_ids = client.add_entities_batch(graph_id, entities)

        return jsonify({
            "success": True,
            "data": {"entity_ids": entity_ids}
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hindsight_bp.route('/graph/<graph_id>/relationships', methods=['GET'])
def get_relationships(graph_id: str):
    """
    Get relationships from a graph

    Query params:
        - entity_id: Filter by entity (optional)
        - include_expired: Include expired relationships (default: false)
        - limit: Max results (default: 100)

    Returns:
    {
        "success": true,
        "data": [...]
    }
    """
    try:
        entity_id = request.args.get("entity_id")
        include_expired = request.args.get("include_expired", "false").lower() == "true"
        limit = int(request.args.get("limit", 100))

        client = get_hindsight_client()
        relationships = client.get_relationships(graph_id, entity_id, include_expired, limit)

        return jsonify({"success": True, "data": relationships})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hindsight_bp.route('/graph/<graph_id>/relationships', methods=['POST'])
def add_relationships(graph_id: str):
    """
    Add relationships to a graph

    Request body:
    {
        "relationships": [
            {
                "source_id": "ent_xxx",
                "target_id": "ent_yyy",
                "type": "KNOWS",
                "fact": "Alice knows Bob",
                "valid_at": "2025-01-01",
                "invalid_at": null
            },
            ...
        ]
    }

    Returns:
    {
        "success": true,
        "data": {
            "relationship_ids": ["rel_xxx", ...]
        }
    }
    """
    try:
        data = request.get_json()
        relationships = data.get("relationships", [])

        if not relationships:
            return jsonify({"success": False, "error": "relationships required"}), 400

        client = get_hindsight_client()
        relationship_ids = client.add_relationships_batch(graph_id, relationships)

        return jsonify({
            "success": True,
            "data": {"relationship_ids": relationship_ids}
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hindsight_bp.route('/graph/<graph_id>/memories', methods=['POST'])
def add_memories(graph_id: str):
    """
    Add memories/episodes to a graph

    Request body:
    {
        "memories": [
            {
                "content": "Alice posted about the event",
                "agent_name": "Alice",
                "round_num": 5,
                "metadata": {...}
            },
            ...
        ]
    }

    Returns:
    {
        "success": true,
        "data": {
            "memory_ids": ["mem_xxx", ...]
        }
    }
    """
    try:
        data = request.get_json()
        memories = data.get("memories", [])

        if not memories:
            return jsonify({"success": False, "error": "memories required"}), 400

        client = get_hindsight_client()
        memory_ids = client.add_memories_batch(graph_id, memories)

        return jsonify({
            "success": True,
            "data": {"memory_ids": memory_ids}
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hindsight_bp.route('/graph/<graph_id>/search', methods=['POST'])
def search_graph(graph_id: str):
    """
    Search the graph using Hindsight's 4-strategy retrieval

    Request body:
    {
        "query": "What happened to Alice?",
        "strategies": ["semantic", "bm25", "graph", "temporal"],  // optional
        "limit": 10,  // optional
        "round_filter": 20  // optional, for temporal search
    }

    Returns:
    {
        "success": true,
        "data": {
            "query": "...",
            "strategies": {
                "semantic": {"entities": [...]},
                "bm25": {"memories": [...]},
                "graph": {"relationships": [...]},
                "temporal": {"memories": [...]}
            },
            "combined_facts": [...],
            "entities": [...],
            "relationships": [...]
        }
    }
    """
    try:
        data = request.get_json()
        query = data.get("query")
        strategies = data.get("strategies")
        limit = data.get("limit", 10)
        round_filter = data.get("round_filter")

        if not query:
            return jsonify({"success": False, "error": "query required"}), 400

        client = get_hindsight_client()
        results = client.search(
            graph_id=graph_id,
            query=query,
            strategies=strategies,
            limit=limit,
            round_filter=round_filter
        )

        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def register_routes(app):
    """Register all checkpoint and hindsight routes with the Flask app"""
    app.register_blueprint(checkpoint_bp)
    app.register_blueprint(hindsight_bp)
