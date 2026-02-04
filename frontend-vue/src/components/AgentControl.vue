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
              请输入你的需求，然后启动，您将看到 Agent 的实时思考与执行过程。
            </p>

            <!-- 用户输入区域 -->
            <div class="action-area" style="margin-bottom: 16px;">
              <el-input
                v-model="userInput"
                type="textarea"
                :rows="3"
                placeholder="例如：帮我生成一份关于 AI 行业的资讯早报，重点关注大模型进展和工具更新。"
              />
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
                <div v-if="intentSummary" class="intent-summary">
                  <h4>🎯 意图理解</h4>
                  <p class="intent-text">{{ intentSummary }}</p>
                </div>
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
import { useAgentControl } from '../composables/useAgentControl'

const {
  // state
  isRunning,
  reportContent,
  logs,
  logContainer,
  userInput,
  intentSummary,
  // computed
  renderedMarkdown,
  // methods
  clearAll,
  handleRunTaskStream,
} = useAgentControl()
</script>

<style src="../styles/agent-control.css"></style>