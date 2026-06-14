'use client'

import {useState} from 'react'
import {actionsApi, automationCycleApi} from '../lib/api'

type ContextAction = {
  label: '手动抓取'|'推送到候选词'|'重新计算'|'补证据'|'推送到关键词库'|'重新验证'|'修正关联'|'推送到机会推进'|'上传 / 更新 PRD'|'运行一轮'|'修复异常'
  actionType: string
  targetType: string
  targetId: string | number
  confirm?: boolean
  variant?: 'primary'|'secondary'
}

type Props = {
  actions: ContextAction[]
}

function submittedMessage(action: ContextAction) {
  if (action.label === '补证据') return '补证据请求已提交，会进入动作队列；需要自动任务执行后才会产生新证据。'
  if (action.label === '运行一轮') return '自动化周期已启动，顶部状态栏会继续显示进度。'
  return `${action.label} 已提交`
}

export function ContextActions({actions}: Props) {
  const [pending, setPending] = useState<string>('')
  const [message, setMessage] = useState<string>('')

  async function run(action: ContextAction) {
    const key = `${action.actionType}:${action.targetType}:${action.targetId}`
    setPending(key)
    setMessage('')
    try {
      if (action.actionType === 'automation.run') {
        await automationCycleApi.run({})
      } else {
        const request = await actionsApi.create({
          action_type: action.actionType,
          target_type: action.targetType,
          target_id: String(action.targetId),
          requested_by: 'user',
          reason: action.label,
          confirm: Boolean(action.confirm),
        })
        if (!action.confirm) await actionsApi.execute(request.id, false)
      }
      setMessage(submittedMessage(action))
    } catch (err) {
      setMessage(err instanceof Error ? err.message : `${action.label} 失败`)
    } finally {
      setPending('')
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {actions.map(action => {
        const key = `${action.actionType}:${action.targetType}:${action.targetId}`
        const cls = action.variant === 'secondary' ? 'btn-secondary' : 'btn'
        return (
          <button key={key} type="button" className={cls} disabled={pending === key} onClick={() => run(action)}>
            {pending === key ? '处理中...' : action.label}
          </button>
        )
      })}
      {message && <span className="text-xs text-slate-400">{message}</span>}
    </div>
  )
}
