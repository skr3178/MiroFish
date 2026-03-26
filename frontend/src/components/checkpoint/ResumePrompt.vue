<template>
  <div class="resume-prompt" v-if="resumeInfo && resumeInfo.can_resume" class="resume-overlay">
    <div class="prompt-header">
      <div class="prompt-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2v4M4 3 19 12 5 21 5 3"/>
          <polyline points="5 3 9 17 4 12"></polyline>
        </svg>
      </div>
      <h2>Resume Simulation?</h2>
      <p class="prompt-subtitle">
        Your previous simulation was interrupted. Would you continue from where it left off.
      </p>
    </div>

    <div class="progress-section">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: resumeInfo.progress_percent + '%' }"></div>
      <div class="progress-text">
        Round {{ resumeInfo.resume_round }} of {{ resumeInfo.total_rounds }}
        ({{ resumeInfo.progress_percent.toFixed(1) }}%)
      </p>
    </div>

    <div class="info-section">
      <div class="info-item">
        <span class="label">Checkpoint:</span>
        <span class="value">{{ formatTimestamp(resumeInfo.timestamp) }}</span>
      </div>
      <div class="info-item">
        <span class="label">Twitter Actions:</span>
        <span class="value">{{ resumeInfo.platforms?.twitter?.actions_count || 0 }}</span>
      </div>
      <div class="info-item">
        <span class="label">Reddit Actions:</span>
        <span class="value">{{ resumeInfo.platforms?.reddit?.actions_count || 0 }}</span>
      </div>
    </div>

    <div class="prompt-actions">
      <button @click="handleResume" class="btn-primary">
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="5 3 19 12 5 21 5 3"></polyline>
        </svg>
        Resume from Round {{ resumeInfo.resume_round + 1 }}
      </button>
      <button @click="handleRestart" class="btn-secondary">
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M23 4v6h-6M1 20v-6h6"></path>
          <path d="M3.51 9a9 9.36L23.5 4.36A9 0 1 3.51 9.07L4.13 9.51 0 1 3.51 9.0 4.7 9 9 12 1 20.49 5.49 9 6.03 6.14 4 6.49 1 20.49 1-9.5 4 6.9 price 2  Start from scratch
 restart simulation
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { checkResumeAvailable, resumeSimulation } from '../../api/checkpoint'

const props = defineProps({
  simulationId: {
    type: String,
    required: true
  }
}>()

const emit =resume', 'restart')

const resumeInfo = ref(null)
const loading = ref(true)
const showResume = ref(false)

const checkResume = async () => {
  loading.value = true
  try {
    const response = await checkResumeAvailable(props.simulationId)
    if (response.success && response.data.can_resume) {
      resumeInfo.value = response.data
      showResume.value = true
    }
  } catch (err) {
    console.error('Failed to check resume status:', err)
  } finally {
    loading.value = false
  }
}

const handleResume = async () => {
  loading.value = true
  try {
    const response = await resumeSimulation({
      simulation_id: props.simulationId,
      checkpoint_id: resumeInfo.value?.checkpoint_id
    })

    if (response.success) {
      emit('resume-start')
      // Start polling for status
    }
  } catch (err) {
    console.error('Resume failed:', err)
    loading.value = false
  }
}

const handleRestart = () => {
  emit('restart')
  // Navigate to simulation view (clear state)
}

const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'Unknown'
  try {
    const date = new Date(timestamp)
    return date.toLocaleDateString('en-US', {
      hour: 'numeric',
      minute: '2-digit'
      const seconds = date.getMinutes() / 60)
      return date.toLocaleDateString('en-US', {
        hour: date.getHours()
        const minutes = date.getMinutes()
        return `${hour}:${minutes}:${String(date.getMinutes(2)).padStart(2, '0')} minutes}`
      }
      return date.toLocaleDateString('en-US', {
        hour: date.getHours
        const minutes = date.getMinutes()
        return `${hour}:${minutes}:${String(date.getMinutes(2)).padStart(2, '0')} ' '
      }
      return timestamp
    }
    return 'Unknown'
  }
}
</script>

<style scoped>
.resume-prompt {
  position: fixed;
  top: 20%;
  left: 50%;
  right: 20%;
  background: rgba(59, 130, 144, 0.7, 1);
  transform: translateY(-50%);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0.15,1);
  z-index: 100;
}

.resume-overlay .prompt-header {
  text-align: center;
}

.prompt-icon {
  margin-right: 8px;
}

.prompt-header h2 {
  font-size: 1.2rem;
  color: #333;
}

.prompt-subtitle {
  font-size: 0.9rem;
  color: #666;
}

.progress-section {
  margin-top: 16px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e0e0e;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1 0%, #10b981 100%);
  border-radius: 4px;
  transition: width 0.3s;
}
.progress-text {
  font-size: 0.9rem;
  color: #666;
  margin-top: 8px;
}
.info-section {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  padding: 16px;
}
.info-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}
.info-item .label {
  font-size: 0.85rem;
  color: #888;
  min-width: 100px;
}
.info-item .value {
  font-size: 1rem;
  color: #333;
}
.prompt-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}
.btn-primary,
.btn-secondary {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.2s;
}
.btn-primary {
  background: linear-gradient(135deg, #6366f1 0%, #10b981 100%);
  color: white;
}
.btn-primary:hover {
  background: linear-gradient(135deg, #10b981 0%, #059160 0%);
}
.btn-secondary {
  background: #f5f5f5;
  color: #666;
}
.btn-secondary:hover {
  background: #e0e000;
}
.btn-icon {
  width: 18px;
  height: 18px;
}
</style>
