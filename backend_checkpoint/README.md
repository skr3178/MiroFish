# MiroFish Checkpoint Extension

This extension adds checkpoint/resume functionality to MiroFish simulations with Hindsight integration (self-hosted, no rate limits).

## Features

- **Automatic Checkpoints**: Save simulation progress every N rounds (default: 5)
- **Resume Support**: Continue interrupted simulations from the last checkpoint
- **Hindsight Integration**: Self-hosted temporal graph memory (replaces Zep Cloud)
- **No Rate Limits**: Uses local PostgreSQL instead of cloud services

## Installation

### 1. Setup PostgreSQL with pgvector

```bash
# Using Docker (recommended)
docker run -d \
  --name mirofish-hindsight \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=mirofish_hindsight \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Hindsight Configuration
HINDSIGHT_HOST=localhost
HINDSIGHT_PORT=5432
HINDSIGHT_DATABASE=mirofish_hindsight
HINDSIGHT_USERNAME=postgres
HINDSIGHT_PASSWORD=your_password

# Checkpoint Configuration
CHECKPOINT_ENABLED=true
CHECKPOINT_INTERVAL=5
CHECKPOINT_KEEP=10
```

### 3. Install Dependencies

```bash
pip install psycopg2-binary
```

## Usage

### Running the Server with Checkpoint API

```bash
# From the project root
python -m backend_checkpoint.run_with_checkpoint_api

# Or with custom options
python -m backend_checkpoint.run_with_checkpoint_api --port 5002 --debug
```

### Running Simulations with Checkpoints

```bash
# Start a new simulation with checkpointing
python -m backend_checkpoint.scripts.run_with_checkpoint \
  --config backend/uploads/simulations/sim_xxx/simulation_config.json \
  --checkpoint-interval 5

# Resume from the latest checkpoint
python -m backend_checkpoint.scripts.run_with_checkpoint \
  --config backend/uploads/simulations/sim_xxx/simulation_config.json \
  --resume-from-checkpoint latest
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/checkpoint/check/resume/<sim_id>` | GET | Check if resume is available |
| `/api/checkpoint/resume` | POST | Resume simulation from checkpoint |
| `/api/checkpoint/checkpoints/<sim_id>` | GET | List all checkpoints |
| `/api/checkpoint/status/<sim_id>` | GET | Get simulation status |
| `/api/hindsight/graph` | POST | Create a Hindsight graph |
| `/api/hindsight/graph/<graph_id>/search` | POST | Search a Hindsight graph |

### Frontend Integration

Import the ResumePrompt component:

```vue
<script setup>
import ResumePrompt from '@/components/checkpoint/ResumePrompt.vue'
</script>

<template>
  <ResumePrompt
    :simulation-id="currentSimulationId"
    @resume="handleResume"
    @restart="handleRestart"
  />
</template>
```

## Integration with Existing Flask App

To integrate with the existing MiroFish Flask app without modifying original files:

```python
# In a custom entry point
from app import create_app
from backend_checkpoint.integration import register_checkpoint_extension

app = create_app()
register_checkpoint_extension(app, prefix="/api")

app.run()
```

## File Structure

```
backend_checkpoint/
├── __init__.py
├── config.py                    # Configuration
├── integration.py               # Flask integration
├── run_with_checkpoint_api.py   # Entry point script
├── api/
│   ├── __init__.py
│   └── checkpoint_routes.py     # REST endpoints
├── services/
│   ├── __init__.py
│   ├── checkpoint_manager.py    # Checkpoint creation/restore
│   ├── resume_manager.py        # Resume detection
│   └── hindsight_client.py      # Hindsight graph client
├── scripts/
│   └── run_with_checkpoint.py   # Simulation with checkpoints
└── utils/
    ├── __init__.py
    └── hindsight_tools.py       # ReportAgent tools
```

## Checkpoint Storage

Checkpoints are stored in:
```
backend/uploads/simulations/sim_xxx/checkpoints/
├── cp_round_5/
│   ├── metadata.json
│   ├── twitter_simulation.db
│   ├── reddit_simulation.db
│   ├── twitter_actions.jsonl
│   └── reddit_actions.jsonl
├── cp_round_10/
└── latest -> cp_round_10/
```
