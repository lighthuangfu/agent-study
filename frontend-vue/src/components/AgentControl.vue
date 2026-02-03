<template>
  <el-container class="full-height">
      <!-- 顶部导航保持不变 -->
      <el-header class="glass-header">
        <div class="header-content">
          <div class="logo-area">
            <span class="logo-icon">🤖</span>
            <span class="logo-text">AI Agent 控制台</span>
          </div>
          <el-tag effect="dark" type="primary" round class="status-tag">System Ready</el-tag>
        </div>
      </el-header>

      <el-main>
        <div class="content-wrapper">
          
          <!-- 控制面板 -->
          <div class="custom-card control-panel">
            <div class="card-title">
              <h3>🕹️ 任务控制中心</h3>
            </div>
            
            <p class="desc-text">
              点击启动后，您将看到 Agent 的实时思考与执行过程。
            </p>

            <div class="action-area">
              <button 
                class="magic-button" 
                @click="handleRunTaskStream" 
                :disabled="isRunning"
                :class="{ 'is-loading': isRunning }"
              >
                <span v-if="!isRunning" class="btn-content">🚀 启动智能体</span>
                <span v-else class="btn-content"><span class="spinner"></span>运行中...</span>
              </button>
            </div>

            <!-- ✨ 新增：思考过程日志窗口 ✨ -->
            <transition name="el-fade-in">
              <div v-if="logs.length > 0 || isRunning" class="terminal-window">
                <div class="terminal-header">
                  <span class="dot red"></span>
                  <span class="dot yellow"></span>
                  <span class="dot green"></span>
                  <span class="title">Agent Runtime Logs</span>
                </div>
                <div class="terminal-body" ref="logContainer">
                  <div v-for="(log, index) in logs" :key="index" class="log-line">
                    <span class="log-time">[{{ log.time }}]</span>
                    <span class="log-content"> > {{ log.message }}</span>
                  </div>
                  <div v-if="isRunning" class="log-line blink-cursor">_</div>
                </div>
              </div>
            </transition>
          </div>

          <!-- 结果展示 -->
          <transition name="el-zoom-in-bottom">
            <div v-if="reportContent" class="custom-card result-panel">
              <div class="card-header-row">
                <h3>📊 执行报告</h3>
                <el-button link type="primary" @click="clearAll">清空</el-button>
              </div>
              <div class="markdown-viewer">
                <div class="markdown-body" v-html="renderedMarkdown"></div>
              </div>
            </div>
          </transition>

        </div>
      </el-main>
      
      <el-footer class="simple-footer">
        Agent Architecture v1.0 • Vue 3 + FastAPI
      </el-footer>
  </el-container>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { marked } from 'marked' 
import { ElMessage } from 'element-plus'

const isRunning = ref(false)
const reportContent = ref('')
const logs = ref([]) // 存储日志列表
const logContainer = ref(null)

const renderedMarkdown = computed(() => marked.parse(reportContent.value))

const clearAll = () => {
  reportContent.value = ''
  logs.value = []
}

// ✨ 核心：流式请求处理函数
const handleRunTaskStream = async () => {
  if (isRunning.value) return
  
  isRunning.value = true
  reportContent.value = ''
  logs.value = []
  
  // 添加初始日志
  addLog("正在初始化 Agent Graph...")

  try {
    const response = await fetch('http://172.16.4.232:8000/run-task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: 'vue_user' })
    })

    if (!response.ok) throw new Error('Network response was not ok')

    // 获取读取器
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      // 解码数据块
      const chunk = decoder.decode(value)
      // 处理 SSE 格式 (data: {...})，可能一次收到多条
      const lines = chunk.split('\n\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonStr = line.slice(6) // 去掉 'data: '
            if (!jsonStr.trim()) continue
            
            const data = JSON.parse(jsonStr)
            
            if (data.type === 'log') {
              addLog(data.message)
            } else if (data.type === 'result') {
              reportContent.value = data.content
              addLog("✅ 任务执行完毕！")
            } else if (data.type === 'error') {
              addLog(`❌ 错误: ${data.message}`)
              ElMessage.error(data.message)
            }
          } catch (e) {
            console.error("解析流数据失败", e)
          }
        }
      }
    }

  } catch (error) {
    console.error(error)
    ElMessage.error('连接中断或后端异常')
    addLog("❌ 连接中断")
  } finally {
    isRunning.value = false
  }
}

// 辅助：添加日志并自动滚动
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  logs.value.push({ time, message: msg })
  
  // 自动滚动到底部
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}
</script>

<style src="../styles/agent-control.css"></style>