<template>
  <div v-if="showPrompt" class="resume-overlay">
    <div class="resume-prompt">
      <div class="prompt-header">
        <svg class="prompt-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
        <h2>Resume Simulation?</h2>
        <p class="prompt-subtitle">
          Your previous simulation was interrupted. Would you like to continue from where you left off?
        </p>
      </div>

      <div class="progress-section">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <p class="progress-text">
          Round {{ resumeInfo.resume_round }} of {{ resumeInfo.total_rounds }}
          ({{ progressPercent.toFixed(1) }}%)
        </p>
      </div>

      <div class="info-section">
        <div class="info-item">
          <span class="label">Checkpoint Time:</span>
          <span class="value">{{ formatTimestamp(resumeInfo.timestamp) }}</span>
        </div>
        <div class="info-item">
          <span class="label">Twitter Actions:</span>
          <span class="value">{{ twitterActions }}</span>
        </div>
        <div class="info-item">
          <span class="label">Reddit Actions:</span>
          <span class="value">{{ redditActions }}</span>
        </div>
      </div>

      <div class="prompt-actions">
        <button @click="handleResume" class="btn-primary">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          </svg>
          Resume from Round {{ resumeInfo.resume_round + 1 }}
        </button>
        <button @click="handleRestart" class="btn-secondary">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6"></path>
            <path d="M1 20v-6h6"></path>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10"></path>
            <path d="M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
          Start New Simulation
        </button>
      </div>
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
})

const emit = defineEmits(['resume', 'restart'])

const resumeInfo = ref(null)
const loading = ref(true)
const showPrompt = ref(false)

const progressPercent = computed(() => {
  if (!resumeInfo.value) return 0
  return resumeInfo.value.progress_percent || 0
})

const twitterActions = computed(() => {
  if (!resumeInfo.value || !resumeInfo.value.platforms) return 0
  return resumeInfo.value.platforms.twitter?.actions_count || 0
})

const redditActions = computed(() => {
  if (!resumeInfo.value || !resumeInfo.value.platforms) return 0
  return resumeInfo.value.platforms.reddit?.actions_count || 0
})

const checkResume = async () => {
  loading.value = true
  try {
    const response = await checkResumeAvailable(props.simulationId)
    if (response.success && response.data && response.data.can_resume) {
      resumeInfo.value = response.data
      showPrompt.value = true
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
      emit('resume', response.data)
      showPrompt.value = false
    }
  } catch (err) {
    console.error('Resume failed:', err)
  } finally {
    loading.value = false
  }
}

const handleRestart = () => {
  emit('restart')
  showPrompt.value = false
}

const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'Unknown'
  try {
    const date = new Date(timestamp)
    return date.toLocaleString()
  } catch {
    return timestamp
  }
}

onMounted(() => {
  checkResume()
})

defineExpose({
  checkResume,
  showPrompt
})
</script>

<style scoped>
.resume-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.resume-prompt {
  background: white;
  border-radius: 12px;
  padding: 24px;
  max-width: 420px;
  width: 90%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.prompt-header {
  text-align: center;
  margin-bottom: 20px;
}

.prompt-icon {
  width: 48px;
  height: 48px;
  color: #6366f1;
  margin-bottom: 12px;
}

.prompt-header h2 {
  margin: 0 0 8px 0;
  font-size: 1.25rem;
  color: #1f2937;
}

.prompt-subtitle {
  margin: 0;
  font-size: 0.875rem;
  color: #6b7280;
}

.progress-section {
  margin-bottom: 20px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1 0%, #10b981 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-text {
  text-align: center;
  font-size: 0.875rem;
  color: #4b5563;
  margin: 0;
}

.info-section {
  background: #f9fafb;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 0.875rem;
}

.info-item .label {
  color: #6b7280;
}

.info-item .value {
  color: #1f2937;
  font-weight: 500;
}

.prompt-actions {
  display: flex;
  gap: 12px;
}

.btn-primary,
.btn-secondary {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}

.btn-secondary {
  background: #f3f4f6;
  color: #4b5563;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

.btn-icon {
  width: 16px;
  height: 16px;
}
</style>
