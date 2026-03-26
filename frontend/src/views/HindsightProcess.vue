<template>
  <div class="process-page">
    <!-- 顶部导航栏 -->
    <nav class="navbar">
      <div class="nav-brand" @click="goHome">MIROFISH</div>

      <!-- 中间步骤指示器 -->
      <div class="nav-center">
        <div class="step-badge">HINDSIGHT</div>
        <div class="step-name">Step 1-2: 构建知识图谱</div>
      </div>

      <div class="nav-status">
        <span class="status-dot" :class="statusClass"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
    </nav>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧: 实时图谱展示 -->
      <div class="left-panel">
        <div class="panel-header">
          <div class="header-left">
            <span class="header-deco">◆</span>
            <span class="header-title">Hindsight 知识图谱</span>
          </div>
          <div class="header-right">
            <template v-if="graphData">
              <span class="stat-item">{{ graphData.node_count || entities.length }} 节点</span>
              <span class="stat-divider">|</span>
              <span class="stat-item">{{ graphData.edge_count || 0 }} 关系</span>
            </template>
            <button class="action-btn" @click="refreshGraph" :disabled="graphLoading">
              <span :class="{ 'spinning': graphLoading }">↻</span>
            </button>
          </div>
        </div>

        <div class="graph-container">
          <!-- 空状态 -->
          <div v-if="!graphData && !graphLoading" class="empty-state">
            <div class="empty-icon">◉</div>
            <div class="empty-text">上传文档后开始构建知识图谱</div>
          </div>

          <!-- 加载状态 -->
          <div v-else-if="graphLoading" class="loading-state">
            <div class="loading-spinner"></div>
            <div class="loading-text">{{ buildProgress.message || '构建中...' }}</div>
            <div class="loading-progress">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: buildProgress.progress + '%' }"></div>
              </div>
              <span class="progress-text">{{ buildProgress.progress }}%</span>
            </div>
          </div>

          <!-- 图谱数据 -->
          <div v-else-if="graphData" class="graph-view">
            <div class="entity-list">
              <div v-for="entity in entities" :key="entity.uuid" class="entity-card" @click="selectEntity(entity)">
                <div class="entity-type">{{ entity.labels?.[1] || 'Entity' }}</div>
                <div class="entity-name">{{ entity.name }}</div>
                <div v-if="entity.summary" class="entity-summary">{{ entity.summary }}</div>
                <div v-if="entity.related_edges?.length" class="entity-relations">
                  {{ entity.related_edges.length }} 关系
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧: 操作面板 -->
      <div class="right-panel">
        <div class="panel-header">
          <span class="header-title">操作面板</span>
        </div>

        <div class="panel-content">
          <!-- Phase 0: 上传文件 -->
          <div v-if="currentPhase === 0" class="phase-section">
            <h3>Step 1: 上传文档</h3>

            <div class="upload-area" @click="triggerFileInput" @dragover.prevent @drop.prevent="handleDrop">
              <input type="file" ref="fileInput" @change="handleFileSelect" multiple accept=".pdf,.txt,.md" hidden />
              <div class="upload-icon">📄</div>
              <div class="upload-text">点击或拖拽文件到此处</div>
              <div class="upload-hint">支持 PDF, TXT, MD 格式</div>
            </div>

            <div v-if="selectedFiles.length" class="file-list">
              <div v-for="(file, idx) in selectedFiles" :key="idx" class="file-item">
                <span class="file-name">{{ file.name }}</span>
                <span class="file-size">{{ formatFileSize(file.size) }}</span>
                <button class="file-remove" @click="removeFile(idx)">×</button>
              </div>
            </div>

            <div class="form-group">
              <label>模拟需求</label>
              <textarea v-model="simulationRequirement" placeholder="描述您想模拟的场景..." rows="3"></textarea>
            </div>

            <button class="btn-primary" @click="startOntologyGeneration" :disabled="!canStartOntology || loading">
              {{ loading ? '处理中...' : '生成本体并构建图谱' }}
            </button>

            <div v-if="error" class="error-message">{{ error }}</div>
          </div>

          <!-- Phase 1: 构建中 -->
          <div v-else-if="currentPhase === 1" class="phase-section">
            <h3>Step 2: 构建知识图谱</h3>

            <div class="build-status">
              <div class="status-icon building">⚙</div>
              <div class="status-text">{{ buildProgress.message || '正在提取实体和关系...' }}</div>
            </div>

            <div class="progress-section">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: buildProgress.progress + '%' }"></div>
              </div>
              <div class="progress-label">{{ buildProgress.progress }}%</div>
            </div>

            <div v-if="ontology" class="ontology-preview">
              <h4>已生成本体</h4>
              <div class="ontology-stats">
                <span>{{ ontology.entity_types?.length || 0 }} 实体类型</span>
                <span>{{ ontology.edge_types?.length || 0 }} 关系类型</span>
              </div>
            </div>
          </div>

          <!-- Phase 2: 完成 -->
          <div v-else-if="currentPhase === 2" class="phase-section">
            <h3>图谱构建完成!</h3>

            <div class="success-icon">✓</div>

            <div class="result-stats">
              <div class="stat-item">
                <span class="stat-value">{{ entities.length }}</span>
                <span class="stat-label">实体</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">{{ totalRelationships }}</span>
                <span class="stat-label">关系</span>
              </div>
            </div>

            <div class="entity-types-list">
              <h4>实体类型</h4>
              <div class="type-tags">
                <span v-for="type in entityTypes" :key="type" class="type-tag">{{ type }}</span>
              </div>
            </div>

            <button class="btn-primary" @click="goToSimulation">
              开始模拟 (Step 3) →
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  generateOntology,
  prepareWithHindsight,
  getPrepareStatus,
  getHindsightEntities
} from '@/api/checkpoint'

const router = useRouter()
const route = useRoute()

// Refs
const fileInput = ref(null)
const selectedFiles = ref([])
const simulationRequirement = ref('')
const loading = ref(false)
const error = ref('')
const currentPhase = ref(0) // 0: upload, 1: building, 2: complete
const ontology = ref(null)
const projectId = ref(null)
const graphId = ref(null)
const taskId = ref(null)
const buildProgress = ref({ progress: 0, message: '' })
const graphData = ref(null)
const graphLoading = ref(false)
const entities = ref([])

// Polling
let pollInterval = null

// Computed
const statusClass = computed(() => {
  if (currentPhase.value === 0) return 'idle'
  if (currentPhase.value === 1) return 'processing'
  return 'success'
})

const statusText = computed(() => {
  if (currentPhase.value === 0) return '准备中'
  if (currentPhase.value === 1) return '构建中'
  return '已完成'
})

const canStartOntology = computed(() => {
  return selectedFiles.value.length > 0 && simulationRequirement.value.trim()
})

const entityTypes = computed(() => {
  const types = new Set()
  entities.value.forEach(e => {
    if (e.labels && e.labels[1]) types.add(e.labels[1])
  })
  return Array.from(types)
})

const totalRelationships = computed(() => {
  let count = 0
  entities.value.forEach(e => {
    if (e.related_edges) count += e.related_edges.length
  })
  return count
})

// Methods
const goHome = () => router.push('/')

const triggerFileInput = () => fileInput.value?.click()

const handleFileSelect = (e) => {
  const files = Array.from(e.target.files)
  selectedFiles.value = [...selectedFiles.value, ...files]
}

const handleDrop = (e) => {
  const files = Array.from(e.dataTransfer.files)
  selectedFiles.value = [...selectedFiles.value, ...files]
}

const removeFile = (idx) => {
  selectedFiles.value.splice(idx, 1)
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const startOntologyGeneration = async () => {
  if (!canStartOntology.value) return

  loading.value = true
  error.value = ''

  try {
    // Build FormData
    const formData = new FormData()
    selectedFiles.value.forEach(file => {
      formData.append('files', file)
    })
    formData.append('simulation_requirement', simulationRequirement.value)

    // Call Hindsight API
    const response = await generateOntology(formData)

    if (response.success) {
      projectId.value = response.data.project_id
      ontology.value = response.data.ontology

      // Auto-start graph building
      await startGraphBuild()
    } else {
      error.value = response.error || '本体生成失败'
    }
  } catch (err) {
    console.error('Ontology generation error:', err)
    error.value = err.message || '网络错误'
  } finally {
    loading.value = false
  }
}

const startGraphBuild = async () => {
  currentPhase.value = 1
  buildProgress.value = { progress: 5, message: '启动图谱构建...' }

  try {
    const response = await prepareWithHindsight({
      project_id: projectId.value,
      graph_name: 'MiroFish Hindsight Graph',
      chunk_size: 500,
      chunk_overlap: 50
    })

    if (response.success) {
      taskId.value = response.data.task_id
      startPolling()
    } else {
      error.value = response.error || '图谱构建启动失败'
      currentPhase.value = 0
    }
  } catch (err) {
    console.error('Graph build error:', err)
    error.value = err.message || '网络错误'
    currentPhase.value = 0
  }
}

const startPolling = () => {
  if (pollInterval) clearInterval(pollInterval)

  pollInterval = setInterval(async () => {
    try {
      const response = await getPrepareStatus(taskId.value)

      if (response.success) {
        const task = response.data
        buildProgress.value = {
          progress: task.progress || 0,
          message: task.message || ''
        }

        if (task.status === 'completed' && task.result) {
          clearInterval(pollInterval)
          graphId.value = task.result.graph_id
          graphData.value = task.result
          await loadEntities()
          currentPhase.value = 2
        } else if (task.status === 'failed') {
          clearInterval(pollInterval)
          error.value = task.error || '图谱构建失败'
          currentPhase.value = 0
        }
      }
    } catch (err) {
      console.error('Polling error:', err)
    }
  }, 2000)
}

const loadEntities = async () => {
  if (!graphId.value) return

  graphLoading.value = true
  try {
    const response = await getHindsightEntities(graphId.value, { enrich: true, limit: 500 })
    if (response.success) {
      entities.value = response.data.entities || []
    }
  } catch (err) {
    console.error('Load entities error:', err)
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  if (graphId.value) loadEntities()
}

const selectEntity = (entity) => {
  console.log('Selected entity:', entity)
  // Could show detail panel here
}

const goToSimulation = () => {
  // Navigate to simulation setup with graph info
  router.push({
    name: 'HindsightSimulation',
    query: {
      project_id: projectId.value,
      graph_id: graphId.value
    }
  })
}

onMounted(() => {
  // Check for existing project in route
  if (route.params.projectId && route.params.projectId !== 'new') {
    projectId.value = route.params.projectId
    // Could load existing project here
  }
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.process-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fafafa;
  font-family: 'Space Grotesk', sans-serif;
}

/* Navbar */
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
  letter-spacing: 1px;
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

.step-name {
  font-weight: 600;
  color: #333;
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

.header-title {
  font-weight: 600;
  color: #333;
}

.header-deco {
  color: #6366f1;
  margin-right: 8px;
}

.stat-item {
  font-size: 13px;
  color: #666;
}

.stat-divider {
  margin: 0 8px;
  color: #ddd;
}

.action-btn {
  background: none;
  border: 1px solid #ddd;
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
}

.action-btn:hover {
  background: #f5f5f5;
}

.spinning {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Graph Container */
.graph-container {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.empty-state, .loading-state {
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

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #eee;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

.progress-bar {
  width: 200px;
  height: 6px;
  background: #eee;
  border-radius: 3px;
  overflow: hidden;
  margin-top: 12px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #10b981);
  transition: width 0.3s;
}

/* Entity List */
.entity-list {
  display: grid;
  gap: 12px;
}

.entity-card {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.entity-card:hover {
  border-color: #6366f1;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.1);
}

.entity-type {
  font-size: 11px;
  color: #6366f1;
  font-weight: 600;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.entity-name {
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.entity-summary {
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
}

.entity-relations {
  font-size: 12px;
  color: #999;
}

/* Panel Content */
.panel-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.phase-section h3 {
  margin-bottom: 20px;
  color: #333;
}

/* Upload Area */
.upload-area {
  border: 2px dashed #ddd;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 16px;
}

.upload-area:hover {
  border-color: #6366f1;
  background: #f9f9ff;
}

.upload-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.upload-text {
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
}

.upload-hint {
  font-size: 13px;
  color: #999;
}

/* File List */
.file-list {
  margin-bottom: 16px;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 6px;
  margin-bottom: 8px;
}

.file-name {
  flex: 1;
  font-size: 13px;
  color: #333;
}

.file-size {
  font-size: 12px;
  color: #999;
  margin-right: 8px;
}

.file-remove {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 16px;
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

.form-group textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
}

/* Button */
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

/* Error */
.error-message {
  margin-top: 12px;
  padding: 12px;
  background: #fef2f2;
  color: #dc2626;
  border-radius: 6px;
  font-size: 13px;
}

/* Build Status */
.build-status {
  text-align: center;
  padding: 20px;
}

.status-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.status-icon.building {
  animation: spin 2s linear infinite;
}

.progress-section {
  margin-top: 20px;
}

.progress-section .progress-bar {
  width: 100%;
  height: 8px;
}

.progress-label {
  text-align: center;
  margin-top: 8px;
  font-size: 13px;
  color: #666;
}

/* Ontology Preview */
.ontology-preview {
  margin-top: 20px;
  padding: 16px;
  background: #f9f9ff;
  border-radius: 8px;
}

.ontology-preview h4 {
  margin-bottom: 8px;
  color: #333;
}

.ontology-stats {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #666;
}

/* Success */
.success-icon {
  font-size: 64px;
  color: #10b981;
  text-align: center;
  margin-bottom: 20px;
}

.result-stats {
  display: flex;
  justify-content: center;
  gap: 32px;
  margin-bottom: 24px;
}

.result-stats .stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 32px;
  font-weight: 700;
  color: #333;
}

.stat-label {
  font-size: 13px;
  color: #666;
}

/* Entity Types */
.entity-types-list {
  margin-bottom: 24px;
}

.entity-types-list h4 {
  margin-bottom: 12px;
  color: #333;
}

.type-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.type-tag {
  padding: 4px 12px;
  background: #f3f4f6;
  border-radius: 16px;
  font-size: 12px;
  color: #4b5563;
}
</style>
