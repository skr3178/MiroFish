/**
 * Checkpoint API Client
 * Provides functions to interact with checkpoint/resume functionality
 */

import service from './index'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001'

/**
 * Check if a simulation can be resumed
 * @param {string} simulationId - Simulation ID
 * @returns {Promise<Object>} Response with can_resume flag and resume info
 */
export const checkResumeAvailable = (simulationId) => {
  return service.get(`${API_BASE_URL}/api/checkpoint/check/resume/${simulationId}`)
}

/**
 * Resume a simulation from a checkpoint
 * @param {Object} data - Resume data
 * @param {string} data.simulation_id - Simulation ID
 * @param {string} [data.checkpoint_id] - Checkpoint ID (optional, defaults to 'latest')
 * @returns {Promise<Object>} Response with resume result
 */
export const resumeSimulation = (data) => {
  const { simulation_id, checkpoint_id } = data
  return service.post(`${API_BASE_URL}/api/checkpoint/resume`, {
    simulation_id: simulation_id,
    checkpoint_id: checkpoint_id || 'latest'
  })
}

/**
 * List checkpoints for a simulation
 * @param {string} simulationId - Simulation ID
 * @returns {Promise<Object>} Response with list of checkpoints
 */
export const listCheckpoints = (simulationId) => {
  return service.get(`${API_BASE_URL}/api/checkpoint/checkpoints/${simulationId}`)
}

/**
 * Get simulation status including resume availability
 * @param {string} simulationId - Simulation ID
 * @returns {Promise<Object>} Response with simulation status
 */
export const getSimulationStatus = (simulationId) => {
  return service.get(`${API_BASE_URL}/api/checkpoint/status/${simulationId}`)
}

/**
 * Create a Hindsight graph
 * @param {Object} data - Graph data
 * @param {string} data.name - Graph name
 * @param {Object} [data.metadata] - Optional metadata
 * @returns {Promise<Object>} Response with graph_id
 */
export const createHindsightGraph = (data) => {
  return service.post(`${API_BASE_URL}/api/hindsight/graph`, data)
}

/**
 * Search a Hindsight graph
 * @param {string} graphId - Graph ID
 * @param {Object} data - Search data
 * @param {string} data.query - Search query
 * @param {string[]} [data.strategies] - Search strategies
 * @param {number} [data.limit] - Max results
 * @returns {Promise<Object>} Search results
 */
export const searchHindsightGraph = (graphId, data) => {
  return service.post(`${API_BASE_URL}/api/hindsight/graph/${graphId}/search`, data)
}

// ==================== Hindsight Flow API ====================

/**
 * Generate ontology from documents (Step 1)
 * @param {FormData} formData - Form data with files and simulation_requirement
 * @returns {Promise<Object>} Response with project_id and ontology
 */
export const generateOntology = (formData) => {
  return service.post(`${API_BASE_URL}/api/checkpoint/ontology/generate`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

/**
 * Build knowledge graph with Hindsight (Step 2: Prepare)
 * @param {Object} data - Prepare data
 * @param {string} data.project_id - Project ID
 * @param {string} [data.graph_name] - Graph name
 * @param {number} [data.chunk_size] - Chunk size
 * @param {number} [data.chunk_overlap] - Chunk overlap
 * @returns {Promise<Object>} Response with task_id
 */
export const prepareWithHindsight = (data) => {
  return service.post(`${API_BASE_URL}/api/checkpoint/prepare`, data)
}

/**
 * Get prepare task status
 * @param {string} taskId - Task ID
 * @returns {Promise<Object>} Task status with progress
 */
export const getPrepareStatus = (taskId) => {
  return service.get(`${API_BASE_URL}/api/checkpoint/prepare/status/${taskId}`)
}

/**
 * Get entities from Hindsight graph
 * @param {string} graphId - Graph ID
 * @param {Object} params - Query parameters
 * @returns {Promise<Object>} Entities list
 */
export const getHindsightEntities = (graphId, params = {}) => {
  const query = new URLSearchParams(params).toString()
  return service.get(`${API_BASE_URL}/api/checkpoint/entities/${graphId}?${query}`)
}

/**
 * Start simulation with checkpoints (Step 3: Simulate)
 * @param {Object} data - Start data
 * @param {string} data.simulation_id - Simulation ID
 * @param {number} [data.checkpoint_interval] - Checkpoint interval (default: 5)
 * @param {number} [data.max_rounds] - Maximum rounds
 * @param {boolean} [data.enable_memory_updates] - Enable Hindsight memory updates
 * @returns {Promise<Object>} Response with process_pid
 */
export const startWithHindsight = (data) => {
  return service.post(`${API_BASE_URL}/api/checkpoint/start`, data)
}

/**
 * Generate report with Hindsight (Step 4: Report)
 * @param {Object} data - Report data
 * @param {string} data.simulation_id - Simulation ID
 * @param {boolean} [data.force_regenerate] - Force regenerate
 * @returns {Promise<Object>} Response with report_id and task_id
 */
export const generateReportWithHindsight = (data) => {
  return service.post(`${API_BASE_URL}/api/checkpoint/generate_report`, data)
}

/**
 * Get report generation status
 * @param {string} taskId - Task ID
 * @returns {Promise<Object>} Task status with progress
 */
export const getReportStatus = (taskId) => {
  return service.get(`${API_BASE_URL}/api/checkpoint/report/status/${taskId}`)
}

/**
 * Health check for Hindsight API
 * @returns {Promise<Object>} Health status
 */
export const hindsightHealthCheck = () => {
  return service.get(`${API_BASE_URL}/api/checkpoint/health`)
}

export default {
  checkResumeAvailable,
  resumeSimulation,
  listCheckpoints,
  getSimulationStatus,
  createHindsightGraph,
  searchHindsightGraph,
  generateOntology,
  prepareWithHindsight,
  getPrepareStatus,
  getHindsightEntities,
  startWithHindsight,
  generateReportWithHindsight,
  getReportStatus,
  hindsightHealthCheck
}
