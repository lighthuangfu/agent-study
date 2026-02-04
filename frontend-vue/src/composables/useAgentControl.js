import { ref, computed, nextTick } from 'vue'
import { marked } from 'marked'
import { ElMessage } from 'element-plus'

export function useAgentControl() {
  const isRunning = ref(false)
  const reportContent = ref('')
  const logs = ref([]) // 存储日志列表
  const logContainer = ref(null)
  const userInput = ref('')
  const intentSummary = ref('')
  const intentRoute = ref('')

  const renderedMarkdown = computed(() => marked.parse(reportContent.value))

  const clearAll = () => {
    reportContent.value = ''
    logs.value = []
    intentSummary.value = ''
    intentRoute.value = ''
  }

  // ✨ 核心：流式请求处理函数
  const handleRunTaskStream = async () => {
    if (isRunning.value) return

    isRunning.value = true
    reportContent.value = ''
    logs.value = []
    intentSummary.value = ''
    intentRoute.value = ''

    // 添加初始日志
    addLog('正在初始化 Agent Graph...')

    try {
      const playload = {
        user_id: 'vue_user',
        user_input: userInput.value || '',
      }
      const response = await fetch('http://172.16.4.232:8000/run-task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(playload),
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
              } else if (data.type === 'intent') {
                intentSummary.value = data.content || ''
                intentRoute.value = data.route || ''
                addLog(
                  `🎯 已理解用户意图，将执行：${
                    intentRoute.value === 'weather'
                      ? '天气简报'
                      : intentRoute.value === 'rss'
                        ? 'RSS 热点订阅'
                        : '当前输入不属于天气或新闻，将直接给出说明'
                  }`
                )
              } else if (data.type === 'result') {
                reportContent.value = data.content
                addLog('✅ 任务执行完毕！')
              } else if (data.type === 'error') {
                addLog(`❌ 错误: ${data.message}`)
                ElMessage.error(data.message)
              }
            } catch (e) {
              console.error('解析流数据失败', e)
            }
          }
        }
      }
    } catch (error) {
      console.error(error)
      ElMessage.error('连接中断或后端异常')
      addLog('❌ 连接中断')
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

  return {
    // state
    isRunning,
    reportContent,
    logs,
    logContainer,
    userInput,
    intentSummary,
    intentRoute,
    // computed
    renderedMarkdown,
    // methods
    clearAll,
    handleRunTaskStream,
  }
}

