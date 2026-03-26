/**
Checkpoint API Client
Provides functions to interact with checkpoint/resume functionality
*/

import service from '../index'

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:5001'

/**
 * Check if a simulation can be resumed
 */
export const checkResumeAvailable = async (simulationId: string) => {
  const response = await service.get(`${API_BASE_URL}/api/checkpoint/check/resume/${simulationId}`)
  return response.data
}

/**
 * Resume a simulation from a checkpoint
 */
export const resumeSimulation = async (data: {
  simulationId: string;
  checkpointId?: string
}) => {
  const response = await service.post(`${API_BASE_URL}/api/checkpoint/resume`, {
    simulation_id: simulationId,
    checkpoint_id: checkpointId
  })
  return response.data
}
/**
 * List checkpoints for a simulation
 */
export const listCheckpoints = async (simulationId: string) => {
  const response = await service.get(`${API_BASE_URL}/api/checkpoint/checkpoints/${simulationId}`)
  return response.data
}
/**
 * Create a manual checkpoint
 */
export const createCheckpoint = async (simulationId: string) => {
  const response = await service.post(`${API_BASE_URL}/api/checkpoint/create`, {
    simulation_id: simulationId
  })
  return response.data
}
