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
      // 后端地址：同机调试用 localhost，或设置 .env 里 VITE_API_BASE_URL
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
      const response = await fetch(`${apiBase}/run-task`, {
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
                        : intentRoute.value === 'doc'
                          ? '用户需求的内容分析（用户需求与天气和新闻都无关时）'
                          : '都不是，我暂时不做操作'
                  }`
                )
              } else if (data.type === 'doc_chunk') {
                // 后端通过 LangGraph messages 模式推送的真实 LLM token 流
                reportContent.value += data.content
              } else if (data.type === 'result') {
                // 若没有收到 token 流，兜底一次性展示完整结果
                if (!reportContent.value) {
                  reportContent.value = data.content
                }
              } else if (data.type === 'error') {
                addLog(`❌ 错误: ${data.message}`)
                ElMessage.error(data.message)
              } else if (data.type === 'chunk') {
                  reportContent.value += data.content
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
  const isTyping = ref(false)

  // 选中改写：选中文本、浮动按钮、改写结果流、加载态
  const selectedText = ref('')
  /** 选区所在区域：'intent' = 意图理解，'report' = 报告正文（reportContent） */
  const selectedTarget = ref('report')
  const showRewriteButton = ref(false)
  const rewriteButtonPosition = ref({ top: 0, left: 0 })
  const rewriteResult = ref('')
  const rewriteHint = ref('') // 用户新增的改写说明/续写内容
  const rewriteLoading = ref(false)
  const rewriteError = ref('')
  const a4BodyRef = ref(null)

  const clearRewrite = () => {
    selectedText.value = ''
    selectedTarget.value = 'report'
    showRewriteButton.value = false
    rewriteResult.value = ''
    rewriteError.value = ''
    rewriteHint.value = ''
  }

  const onDocumentSelection = () => {
    const sel = window.getSelection()
    const text = (sel && sel.toString() || '').trim()
    if (!text) {
      showRewriteButton.value = false
      selectedText.value = ''
      return
    }
    const container = a4BodyRef.value
    if (!container || !container.contains(sel.anchorNode)) {
      showRewriteButton.value = false
      selectedText.value = ''
      return
    }
    selectedText.value = text
    // 判断选区在意图理解区还是报告正文区，应用替换时更新对应数据
    const intentEl = container.querySelector('.intent-summary')
    selectedTarget.value = intentEl && intentEl.contains(sel.anchorNode) ? 'intent' : 'report'
    try {
      const range = sel.getRangeAt(0)
      const rect = range.getBoundingClientRect()
      rewriteButtonPosition.value = {
        top: rect.bottom + 6,
        left: rect.left,
      }
      showRewriteButton.value = true
    } catch (_) {
      showRewriteButton.value = true
      rewriteButtonPosition.value = { top: 0, left: 0 }
    }
  }

  const requestRewrite = async () => {
    if (!selectedText.value || rewriteLoading.value) return
    rewriteLoading.value = true
    rewriteResult.value = ''
    rewriteError.value = ''
    showRewriteButton.value = false

    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    try {
      const response = await fetch(`${apiBase}/rewrite-selection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: selectedText.value, hint: rewriteHint.value }),
      })
      if (!response.ok) throw new Error('请求失败')
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n\n')
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'chunk' && data.content) rewriteResult.value += data.content
            if (data.type === 'error') rewriteError.value = data.message || '改写失败'
          } catch (_) {}
        }
      }
    } catch (e) {
      rewriteError.value = e.message || '网络错误'
    } finally {
      rewriteLoading.value = false
    }
  }

  /**
   * 将改写结果替换回页面：根据选区所在区域更新 intentSummary 或 reportContent。
   * 先尝试精确匹配；若不存在则按“忽略多余空白”查找并替换第一处。
   */
  const doReplaceIn = (content, orig, replacement) => {
    if (!content || !orig) return content
    if (content.includes(orig)) return content.replace(orig, replacement)
    const escaped = orig.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const flexibleWhitespace = escaped.replace(/\s+/g, '\\s+').trim()
    const re = new RegExp(flexibleWhitespace, 's')
    const match = content.match(re)
    if (match && match[0]) return content.replace(match[0], replacement)
    return content
  }

  const applyRewrite = () => {
    if (!rewriteResult.value || !selectedText.value) return
    const orig = selectedText.value
    const replacement = rewriteResult.value

    if (selectedTarget.value === 'intent') {
      intentSummary.value = doReplaceIn(intentSummary.value, orig, replacement)
    } else {
      reportContent.value = doReplaceIn(reportContent.value, orig, replacement)
    }
    clearRewrite()
  }

  const playTypewriter = async (fullText, speed = 50) => {
    isTyping.value = true
    reportContent.value = ''

    for (let i = 0; i < fullText.length; i++) {
      reportContent.value += fullText[i]
      await new Promise((resolve) => setTimeout(resolve, speed))
      // 定期自动滚动到页面底部，保证最新内容在视口内
      if (i % 5 === 0) {
        await nextTick()
        window.scrollTo({
          top: document.documentElement.scrollHeight,
          behavior: 'smooth',
        })
      }
    }

    isTyping.value = false
    addLog('✅ 任务执行完毕！')
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
    // rewrite
    selectedText,
    showRewriteButton,
    rewriteButtonPosition,
    rewriteResult,
    rewriteHint,
    rewriteLoading,
    rewriteError,
    a4BodyRef,
    // computed
    renderedMarkdown,
    // methods
    clearAll,
    handleRunTaskStream,
    onDocumentSelection,
    requestRewrite,
    applyRewrite,
    clearRewrite,
  }
}

