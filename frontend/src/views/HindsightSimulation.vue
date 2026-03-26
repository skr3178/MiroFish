<template>
  <div class="simulation-page">
    <!-- 顶部导航栏 -->
    <nav class="navbar">
      <div class="nav-brand" @click="goHome">MIROFISH</div>

      <div class="nav-center">
        <div class="step-badge">HINDSIGHT</div>
        <div class="step-name">Step 3: 运行模拟</div>
      </div>

      <div class="nav-status">
        <span class="status-dot" :class="statusClass"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
    </nav>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧: 模拟状态 -->
      <div class="left-panel">
        <div class="panel-header">
          <span class="header-title">模拟进度</span>
          <span v-if="simulationStatus" class="status-badge" :class="simulationStatus">
            {{ simulationStatus }}
          </span>
        </div>

        <div class="simulation-container">
          <!-- 空状态 -->
          <div v-if="!simulationStarted" class="empty-state">
            <div class="empty-icon">▶</div>
            <div class="empty-text">配置并开始模拟</div>
          </div>

          <!-- 运行中 -->
          <div v-else class="simulation-running">
            <div class="progress-section">
              <div class="progress-header">
                <span>Round {{ currentRound }} / {{ totalRounds }}</span>
                <span>{{ progressPercent.toFixed(1) }}%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
              </div>
            </div>

            <div class="stats-grid">
              <div class="stat-card">
                <span class="stat-value">{{ twitterActions }}</span>
                <span class="stat-label">Twitter Actions</span>
              </div>
              <div class="stat-card">
                <span class="stat-value">{{ redditActions }}</span>
                <span class="stat-label">Reddit Actions</span>
              </div>
              <div class="stat-card">
                <span class="stat-value">{{ checkpointsCreated }}</span>
                <span class="stat-label">Checkpoints</span>
              </div>
              <div class="stat-card">
                <span class="stat-value">{{ elapsedTime }}</span>
                <span class="stat-label">Elapsed</span>
              </div>
            </div>

            <!-- Recent Actions -->
            <div class="recent-actions">
              <h4>Recent Actions</h4>
              <div class="action-list">
                <div v-for="action in recentActions" :key="action.timestamp" class="action-item">
                  <span class="action-agent">{{ action.agent_name }}</span>
                  <span class="action-type">{{ action.action_type }}</span>
                  <span class="action-platform">{{ action.platform }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧: 配置面板 -->
      <div class="right-panel">
        <div class="panel-header">
          <span class="header-title">模拟配置</span>
        </div>

        <div class="panel-content">
          <!-- 配置表单 -->
          <div v-if="!simulationStarted" class="config-section">
            <h3>配置参数</h3>

            <div class="form-group">
              <label>模拟总时长 (小时)</label>
              <input type="number" v-model="config.totalHours" min="1" max="168" />
            </div>

            <div class="form-group">
              <label>每轮时长 (分钟)</label>
              <input type="number" v-model="config.minutesPerRound" min="5" max="120" />
            </div>

            <div class="form-group">
              <label>检查点间隔 (轮)</label>
              <input type="number" v-model="config.checkpointInterval" min="1" max="20" />
              <span class="form-hint">每 N 轮保存一次进度</span>
            </div>

            <div class="form-group">
              <label>最大轮数 (可选)</label>
              <input type="number" v-model="config.maxRounds" min="1" placeholder="留空则不限制" />
            </div>

            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="config.enableMemoryUpdates" />
                <span>启用 Hindsight 记忆更新</span>
              </label>
            </div>

            <div class="info-box">
              <strong>预计参数:</strong>
              <ul>
                <li>总轮数: {{ estimatedRounds }} 轮</li>
                <li>检查点数: ~{{ estimatedCheckpoints }} 个</li>
              </ul>
            </div>

            <button class="btn-primary" @click="startSimulation" :disabled="starting">
              {{ starting ? '启动中...' : '开始模拟' }}
            </button>

            <div v-if="error" class="error-message">{{ error }}</div>
          </div>

          <!-- 运行中控制 -->
          <div v-else class="control-section">
            <h3>模拟控制</h3>

            <div class="control-buttons">
              <button class="btn-secondary" @click="pauseSimulation" :disabled="simulationStatus !== 'running'">
                暂停
              </button>
              <button class="btn-danger" @click="stopSimulation" :disabled="simulationStatus === 'stopped'">
                停止
              </button>
            </div>

            <div class="checkpoint-section">
              <h4>检查点</h4>
              <div class="checkpoint-list">
                <div v-for="cp in checkpoints" :key="cp.checkpoint_id" class="checkpoint-item">
                  <span class="cp-round">Round {{ cp.round }}</span>
                  <span class="cp-time">{{ formatTime(cp.timestamp) }}</span>
                </div>
                <div v-if="!checkpoints.length" class="no-data">暂无检查点</div>
              </div>
            </div>

            <button
              class="btn-primary"
              @click="goToReport"
              :disabled="simulationStatus !== 'completed'"
            >
              {{ simulationStatus === 'completed' ? '生成报告 →' : '模拟进行中...' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Resume Prompt -->
    <ResumePrompt
      v-if="showResumePrompt"
      :simulation-id="simulationId"
      @resume="handleResume"
      @restart="handleRestart"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  startWithHindsight,
  checkResumeAvailable,
  listCheckpoints
} from '@/api/checkpoint'
import ResumePrompt from '@/components/checkpoint/ResumePrompt.vue'

const router = useRouter()
const route = useRoute()

// Route params
const projectId = ref(route.query.project_id)
const graphId = ref(route.query.graph_id)
const simulationId = ref(route.query.simulation_id)

// Config
const config = ref({
  totalHours: 72,
  minutesPerRound: 30,
  checkpointInterval: 5,
  maxRounds: null,
  enableMemoryUpdates: true
})

// State
const starting = ref(false)
const simulationStarted = ref(false)
const simulationStatus = ref('idle')
const currentRound = ref(0)
const totalRounds = ref(0)
const twitterActions = ref(0)
const redditActions = ref(0)
const checkpointsCreated = ref(0)
const elapsedTime = ref('00:00:00')
const recentActions = ref([])
const checkpoints = ref([])
const error = ref('')
const showResumePrompt = ref(false)

// Polling
let statusInterval = null
let startTime = null

// Computed
const statusClass = computed(() => {
  if (simulationStatus.value === 'running') return 'processing'
  if (simulationStatus.value === 'completed') return 'success'
  if (simulationStatus.value === 'paused') return 'warning'
  return 'idle'
})

const statusText = computed(() => {
  const texts = {
    idle: '未开始',
    running: '运行中',
    paused: '已暂停',
    stopped: '已停止',
    completed: '已完成'
  }
  return texts[simulationStatus.value] || '未知'
})

const progressPercent = computed(() => {
  if (!totalRounds.value) return 0
  return (currentRound.value / totalRounds.value) * 100
})

const estimatedRounds = computed(() => {
  return (config.value.totalHours * 60) / config.value.minutesPerRound
})

const estimatedCheckpoints = computed(() => {
  return Math.floor(estimatedRounds.value / config.value.checkpointInterval)
})

// Methods
const goHome = () => router.push('/')

const startSimulation = async () => {
  starting.value = true
  error.value = ''

  try {
    const response = await startWithHindsight({
      project_id: projectId.value,
      graph_id: graphId.value,
      total_hours: config.value.totalHours,
      minutes_per_round: config.value.minutesPerRound,
      checkpoint_interval: config.value.checkpointInterval,
      max_rounds: config.value.maxRounds || null,
      enable_memory_updates: config.value.enableMemoryUpdates
    })

    if (response.success) {
      simulationId.value = response.data.simulation_id
      simulationStarted.value = true
      simulationStatus.value = 'running'
      totalRounds.value = estimatedRounds.value
      startTime = Date.now()

      startStatusPolling()
    } else {
      error.value = response.error || '启动失败'
    }
  } catch (err) {
    console.error('Start simulation error:', err)
    error.value = err.message || '网络错误'
  } finally {
    starting.value = false
  }
}

const startStatusPolling = () => {
  if (statusInterval) clearInterval(statusInterval)

  statusInterval = setInterval(async () => {
    try {
      // Poll simulation status
      // This would call a status endpoint
      updateElapsedTime()
    } catch (err) {
      console.error('Status polling error:', err)
    }
  }, 2000)
}

const updateElapsedTime = () => {
  if (!startTime) return
  const elapsed = Date.now() - startTime
  const hours = Math.floor(elapsed / 3600000)
  const minutes = Math.floor((elapsed % 3600000) / 60000)
  const seconds = Math.floor((elapsed % 60000) / 1000)
  elapsedTime.value = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
}

const pauseSimulation = () => {
  simulationStatus.value = 'paused'
}

const stopSimulation = () => {
  if (statusInterval) clearInterval(statusInterval)
  simulationStatus.value = 'stopped'
}

const goToReport = () => {
  router.push({
    name: 'HindsightReport',
    query: {
      simulation_id: simulationId.value,
      graph_id: graphId.value
    }
  })
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString()
}

const handleResume = (data) => {
  showResumePrompt.value = false
  simulationStarted.value = true
  simulationStatus.value = 'running'
  currentRound.value = data.resume_from_round || 0
  startStatusPolling()
}

const handleRestart = () => {
  showResumePrompt.value = false
}

const checkForResume = async () => {
  if (!simulationId.value) return

  try {
    const response = await checkResumeAvailable(simulationId.value)
    if (response.success && response.data?.can_resume) {
      showResumePrompt.value = true
    }
  } catch (err) {
    console.error('Resume check error:', err)
  }
}

const loadCheckpoints = async () => {
  if (!simulationId.value) return

  try {
    const response = await listCheckpoints(simulationId.value)
    if (response.success) {
      checkpoints.value = response.data.checkpoints || []
    }
  } catch (err) {
    console.error('Load checkpoints error:', err)
  }
}

onMounted(() => {
  // Check for existing simulation to resume
  if (simulationId.value) {
    checkForResume()
    loadCheckpoints()
  }
})

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
})
</script>

<style scoped>
.simulation-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fafafa;
  font-family: 'Space Grotesk', sans-serif;
}

/* Navbar - same as HindsightProcess */
.navbar {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #eee;
}

.nav-brand {
  font-weight: 800;
  font-size: 18px;
  cursor: pointer;
}

.nav-center {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-badge {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.nav-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ccc;
}

.status-dot.processing {
  background: #f59e0b;
  animation: pulse 1s infinite;
}

.status-dot.success {
  background: #10b981;
}

.status-dot.warning {
  background: #f59e0b;
}

@keyframes pulse {
  50% { opacity: 0.5; }
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.left-panel, .right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #eee;
}

.right-panel {
  border-right: none;
  max-width: 400px;
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.running {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-badge.completed {
  background: #d1fae5;
  color: #059669;
}

.status-badge.paused {
  background: #fef3c7;
  color: #d97706;
}

/* Simulation Container */
.simulation-container {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

/* Progress Section */
.progress-section {
  margin-bottom: 24px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
}

.progress-bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1 0%, #10b981 100%);
  transition: width 0.3s;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #333;
}

.stat-label {
  font-size: 12px;
  color: #666;
}

/* Recent Actions */
.recent-actions h4 {
  margin-bottom: 12px;
  color: #333;
}

.action-list {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.action-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid #f5f5f5;
  font-size: 13px;
}

.action-item:last-child {
  border-bottom: none;
}

.action-agent {
  font-weight: 500;
  color: #333;
}

.action-type {
  color: #666;
}

.action-platform {
  font-size: 11px;
  color: #999;
  text-transform: uppercase;
}

/* Panel Content */
.panel-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.config-section h3, .control-section h3 {
  margin-bottom: 20px;
  color: #333;
}

/* Form */
.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
  color: #333;
}

.form-group input[type="number"] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.form-hint {
  display: block;
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

/* Info Box */
.info-box {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
  font-size: 13px;
}

.info-box ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
}

/* Buttons */
.btn-primary {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  flex: 1;
  padding: 12px;
  background: #f3f4f6;
  color: #4b5563;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.btn-danger {
  flex: 1;
  padding: 12px;
  background: #fef2f2;
  color: #dc2626;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.control-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

/* Checkpoint Section */
.checkpoint-section {
  margin-bottom: 24px;
}

.checkpoint-section h4 {
  margin-bottom: 12px;
  color: #333;
}

.checkpoint-list {
  background: #f9fafb;
  border-radius: 8px;
  padding: 12px;
  max-height: 150px;
  overflow-y: auto;
}

.checkpoint-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;
}

.no-data {
  text-align: center;
  color: #999;
  font-size: 13px;
}

.error-message {
  margin-top: 12px;
  padding: 12px;
  background: #fef2f2;
  color: #dc2626;
  border-radius: 6px;
  font-size: 13px;
}
</style>
