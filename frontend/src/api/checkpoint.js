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

export default {
  checkResumeAvailable,
  resumeSimulation,
  listCheckpoints,
  getSimulationStatus,
  createHindsightGraph,
  searchHindsightGraph
}
