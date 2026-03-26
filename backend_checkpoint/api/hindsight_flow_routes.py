"""
Hindsight Flow API Routes
Complete simulation flow using Hindsight instead of Zep

Endpoints:
- POST /api/checkpoint/prepare - Build graph with Hindsight (Step 2)
- GET /api/checkpoint/prepare/status/<task_id> - Check prepare progress
- POST /api/checkpoint/start - Start simulation with checkpoints (Step 3)
- POST /api/checkpoint/generate_report - Generate report using Hindsight (Step 4)
"""

import os
import sys
import json
import uuid
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Blueprint, request, jsonify, current_app

# Setup paths
_checkpoint_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _checkpoint_dir)

from services.hindsight_client import get_hindsight_client
from services.hindsight_graph_builder import HindsightGraphBuilder, get_graph_builder
from services.checkpoint_manager import CheckpointManager
from services.resume_manager import ResumeManager


# Blueprint
hindsight_flow_bp = Blueprint('hindsight_flow', __name__)

# Task storage (in production, use Redis or database)
_tasks: Dict[str, Dict[str, Any]] = {}


# ==================== Ontology Generation ====================

@hindsight_flow_bp.route('/ontology/generate', methods=['POST'])
def generate_ontology():
    """
    Generate ontology from documents

    Input:
    - files: Document files (multipart)
    - simulation_requirement: What to simulate

    Output:
    - project_id: Project ID
    - ontology: Entity and relationship types
    """
    try:
        # Check for files
        if 'files' not in request.files:
            return jsonify({
                "success": False,
                "error": "No files provided"
            }), 400

        files = request.files.getlist('files')
        simulation_requirement = request.form.get('simulation_requirement', '')
        project_name = request.form.get('project_name', 'Untitled Project')

        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": "simulation_requirement is required"
            }), 400

        # Extract text from files
        documents = []
        for file in files:
            if file.filename:
                content = file.read().decode('utf-8', errors='ignore')
                documents.append(content)

        if not documents:
            return jsonify({
                "success": False,
                "error": "No valid documents found"
            }), 400

        # Create project
        project_id = f"proj_{uuid.uuid4().hex[:12]}"

        # Generate ontology using HindsightGraphBuilder
        builder = get_graph_builder()
        ontology = builder.extract_ontology(documents, simulation_requirement)

        # Store project data
        project_dir = os.path.join(
            current_app.root_path, '..', 'uploads', 'projects', project_id
        )
        os.makedirs(project_dir, exist_ok=True)

        project_data = {
            "project_id": project_id,
            "name": project_name,
            "simulation_requirement": simulation_requirement,
            "ontology": ontology.to_dict(),
            "documents_count": len(documents),
            "created_at": datetime.now().isoformat()
        }

        with open(os.path.join(project_dir, 'project.json'), 'w') as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)

        # Save documents
        docs_dir = os.path.join(project_dir, 'documents')
        os.makedirs(docs_dir, exist_ok=True)
        for i, doc in enumerate(documents):
            with open(os.path.join(docs_dir, f'doc_{i}.txt'), 'w') as f:
                f.write(doc)

        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "ontology": ontology.to_dict(),
                "documents_count": len(documents)
            }
        })

    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ==================== Graph Building (Prepare) ====================

@hindsight_flow_bp.route('/prepare', methods=['POST'])
def prepare_graph():
    """
    Build knowledge graph using Hindsight (Step 2: Prepare)

    Input:
    - project_id: Project ID from ontology generation
    - graph_name: Optional graph name
    - chunk_size: Text chunk size (default: 500)
    - chunk_overlap: Chunk overlap (default: 50)

    Output:
    - task_id: Task ID for progress tracking
    - graph_id: Graph ID (once complete)
    """
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')

        if not project_id:
            return jsonify({
                "success": False,
                "error": "project_id is required"
            }), 400

        # Load project
        project_path = os.path.join(
            current_app.root_path, '..', 'uploads', 'projects', project_id, 'project.json'
        )
        if not os.path.exists(project_path):
            return jsonify({
                "success": False,
                "error": f"Project not found: {project_id}"
            }), 404

        with open(project_path, 'r') as f:
            project = json.load(f)

        # Load documents
        docs_dir = os.path.join(
            current_app.root_path, '..', 'uploads', 'projects', project_id, 'documents'
        )
        documents = []
        if os.path.exists(docs_dir):
            for filename in sorted(os.listdir(docs_dir)):
                with open(os.path.join(docs_dir, filename), 'r') as f:
                    documents.append(f.read())

        # Create task
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        _tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "message": "Starting graph build...",
            "result": None,
            "error": None
        }

        # Build graph in background
        def build_worker():
            try:
                _tasks[task_id]["status"] = "processing"
                _tasks[task_id]["message"] = "Building knowledge graph..."

                builder = get_graph_builder()

                # Reconstruct ontology
                from services.hindsight_graph_builder import Ontology
                ontology = Ontology(
                    entity_types=project['ontology'].get('entity_types', []),
                    edge_types=project['ontology'].get('edge_types', []),
                    analysis_summary=project['ontology'].get('analysis_summary', '')
                )

                def progress_callback(msg: str, progress: int):
                    _tasks[task_id]["progress"] = progress
                    _tasks[task_id]["message"] = msg

                result = builder.build_graph(
                    documents=documents,
                    ontology=ontology,
                    graph_name=data.get('graph_name', project.get('name', 'MiroFish Graph')),
                    chunk_size=data.get('chunk_size', 500),
                    chunk_overlap=data.get('chunk_overlap', 50),
                    progress_callback=progress_callback
                )

                # Update project with graph_id
                project['graph_id'] = result.graph_id
                project['graph_build_result'] = result.to_dict()
                with open(project_path, 'w') as f:
                    json.dump(project, f, indent=2, ensure_ascii=False)

                _tasks[task_id]["status"] = "completed"
                _tasks[task_id]["progress"] = 100
                _tasks[task_id]["message"] = "Graph building complete"
                _tasks[task_id]["result"] = result.to_dict()

            except Exception as e:
                import traceback
                _tasks[task_id]["status"] = "failed"
                _tasks[task_id]["error"] = str(e)
                _tasks[task_id]["traceback"] = traceback.format_exc()

        thread = threading.Thread(target=build_worker)
        thread.daemon = True
        thread.start()

        return jsonify({
            "success": True,
            "data": {
                "task_id": task_id,
                "project_id": project_id,
                "message": "Graph build task started"
            }
        })

    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@hindsight_flow_bp.route('/prepare/status/<task_id>', methods=['GET'])
def get_prepare_status(task_id: str):
    """Get status of graph building task"""
    task = _tasks.get(task_id)

    if not task:
        return jsonify({
            "success": False,
            "error": f"Task not found: {task_id}"
        }), 404

    return jsonify({
        "success": True,
        "data": task
    })


# ==================== Entity Retrieval ====================

@hindsight_flow_bp.route('/entities/<graph_id>', methods=['GET'])
def get_entities(graph_id: str):
    """
    Get entities from Hindsight graph

    Query params:
    - entity_types: Comma-separated entity types to filter
    - enrich: Include relationships (default: true)
    - limit: Max entities (default: 500)
    """
    try:
        entity_types = request.args.get('entity_types', '')
        enrich = request.args.get('enrich', 'true').lower() == 'true'
        limit = int(request.args.get('limit', 500))

        builder = get_graph_builder()

        types_list = entity_types.split(',') if entity_types else None

        entities = builder.get_entities(
            graph_id=graph_id,
            entity_types=types_list,
            enrich_with_edges=enrich,
            limit=limit
        )

        return jsonify({
            "success": True,
            "data": {
                "entities": [e.to_dict() for e in entities],
                "total_count": len(entities)
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==================== Simulation Start ====================

@hindsight_flow_bp.route('/start', methods=['POST'])
def start_simulation():
    """
    Start simulation with Hindsight + checkpoints (Step 3: Simulate)

    Input:
    - simulation_id: Simulation ID
    - checkpoint_interval: Create checkpoint every N rounds (default: 5)
    - max_rounds: Maximum rounds (optional)
    - enable_memory_updates: Write to Hindsight (default: true)

    Output:
    - simulation_id: Simulation ID
    - process_pid: Process ID
    - status: Status
    """
    try:
        data = request.get_json() or {}
        simulation_id = data.get('simulation_id')

        if not simulation_id:
            return jsonify({
                "success": False,
                "error": "simulation_id is required"
            }), 400

        # Check simulation exists
        sim_dir = os.path.join(
            current_app.root_path, '..', 'uploads', 'simulations', simulation_id
        )
        if not os.path.exists(sim_dir):
            return jsonify({
                "success": False,
                "error": f"Simulation not found: {simulation_id}"
            }), 404

        # Check for resume
        checkpoint_interval = data.get('checkpoint_interval', 5)
        max_rounds = data.get('max_rounds')
        enable_memory_updates = data.get('enable_memory_updates', True)

        # Start simulation in subprocess
        import subprocess

        cmd = [
            sys.executable,
            '-m', 'backend_checkpoint.scripts.run_hindsight_simulation',
            '--simulation-id', simulation_id,
            '--checkpoint-interval', str(checkpoint_interval)
        ]

        if not enable_memory_updates:
            cmd.append('--no-memory-updates')

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=current_app.root_path
        )

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "process_pid": process.pid,
                "status": "running",
                "checkpoint_interval": checkpoint_interval
            }
        })

    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ==================== Report Generation ====================

@hindsight_flow_bp.route('/generate_report', methods=['POST'])
def generate_report():
    """
    Generate report using Hindsight search (Step 4: Report)

    Input:
    - simulation_id: Simulation ID
    - force_regenerate: Force regenerate (default: false)

    Output:
    - report_id: Report ID
    - task_id: Task ID for tracking
    """
    try:
        data = request.get_json() or {}
        simulation_id = data.get('simulation_id')

        if not simulation_id:
            return jsonify({
                "success": False,
                "error": "simulation_id is required"
            }), 400

        # Load simulation and project
        sim_path = os.path.join(
            current_app.root_path, '..', 'uploads', 'simulations', simulation_id, 'state.json'
        )
        if not os.path.exists(sim_path):
            return jsonify({
                "success": False,
                "error": f"Simulation not found: {simulation_id}"
            }), 404

        with open(sim_path, 'r') as f:
            sim_state = json.load(f)

        # Get graph_id from project
        project_id = sim_state.get('project_id')
        if not project_id:
            return jsonify({
                "success": False,
                "error": "No project associated with simulation"
            }), 400

        project_path = os.path.join(
            current_app.root_path, '..', 'uploads', 'projects', project_id, 'project.json'
        )
        with open(project_path, 'r') as f:
            project = json.load(f)

        graph_id = project.get('graph_id')
        if not graph_id:
            return jsonify({
                "success": False,
                "error": "No graph associated with project"
            }), 400

        # Create report task
        report_id = f"report_{uuid.uuid4().hex[:12]}"
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        _tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "message": "Starting report generation...",
            "result": None,
            "error": None
        }

        # Generate report in background using Hindsight tools
        def report_worker():
            try:
                _tasks[task_id]["status"] = "processing"
                _tasks[task_id]["message"] = "Generating report with Hindsight..."

                from utils.hindsight_tools import HindsightToolsService

                tools = HindsightToolsService(get_hindsight_client())

                # Get simulation context
                simulation_requirement = project.get('simulation_requirement', '')

                # Search for relevant facts
                context_result = tools.get_simulation_context(
                    graph_id=graph_id,
                    simulation_requirement=simulation_requirement,
                    limit=30
                )

                # Build report structure
                report_dir = os.path.join(
                    current_app.root_path, '..', 'uploads', 'reports', report_id
                )
                os.makedirs(report_dir, exist_ok=True)

                report_data = {
                    "report_id": report_id,
                    "simulation_id": simulation_id,
                    "graph_id": graph_id,
                    "status": "completed",
                    "created_at": datetime.now().isoformat(),
                    "context": context_result.to_dict() if hasattr(context_result, 'to_dict') else context_result,
                    "sections": [
                        {
                            "title": "Simulation Overview",
                            "content": f"Analysis of: {simulation_requirement}"
                        },
                        {
                            "title": "Key Entities",
                            "content": f"Found {context_result.get('total_nodes', 0) if isinstance(context_result, dict) else 0} entities in the knowledge graph"
                        }
                    ]
                }

                with open(os.path.join(report_dir, 'report.json'), 'w') as f:
                    json.dump(report_data, f, indent=2, ensure_ascii=False)

                _tasks[task_id]["status"] = "completed"
                _tasks[task_id]["progress"] = 100
                _tasks[task_id]["message"] = "Report generation complete"
                _tasks[task_id]["result"] = {
                    "report_id": report_id,
                    "report_path": f"/reports/{report_id}"
                }

            except Exception as e:
                import traceback
                _tasks[task_id]["status"] = "failed"
                _tasks[task_id]["error"] = str(e)
                _tasks[task_id]["traceback"] = traceback.format_exc()

        thread = threading.Thread(target=report_worker)
        thread.daemon = True
        thread.start()

        return jsonify({
            "success": True,
            "data": {
                "report_id": report_id,
                "task_id": task_id,
                "status": "generating"
            }
        })

    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@hindsight_flow_bp.route('/report/status/<task_id>', methods=['GET'])
def get_report_status(task_id: str):
    """Get status of report generation task"""
    task = _tasks.get(task_id)

    if not task:
        return jsonify({
            "success": False,
            "error": f"Task not found: {task_id}"
        }), 404

    return jsonify({
        "success": True,
        "data": task
    })


# ==================== Health Check ====================

@hindsight_flow_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        client = get_hindsight_client()
        # Try a simple query
        client.get_graph_info("nonexistent")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return jsonify({
        "success": True,
        "data": {
            "service": "Hindsight Flow API",
            "database": db_status,
            "timestamp": datetime.now().isoformat()
        }
    })
