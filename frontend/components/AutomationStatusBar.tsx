'use client'

import {useEffect, useMemo, useState} from 'react'
import {actionsApi, automationCycleApi, type ActionRequest} from '../lib/api'

type RunRow = {
  id: number
  status: string
  summary?: any
  started_at?: string
  finished_at?: string | null
}

function resultSummary(row: ActionRequest) {
  const result = row.result_json as any
  if (result?.summary) return String(result.summary)
  if (row.reason) return row.reason
  return row.action_type
}

function statusLabel(status: string) {
  if (status === 'running') return '运行中'
  if (status === 'pending') return '排队中'
  if (status === 'failed') return '失败'
  if (status === 'success') return '完成'
  if (status === 'needs_confirmation') return '需确认'
  return status || '未知'
}

export function AutomationStatusBar() {
  const [actions, setActions] = useState<ActionRequest[]>([])
  const [runs, setRuns] = useState<RunRow[]>([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [actionRows, runRows] = await Promise.all([
          actionsApi.list('?limit=20').catch(() => []),
          automationCycleApi.runs().catch(() => []),
        ])
        if (!cancelled) {
          setActions(actionRows)
          setRuns(runRows as RunRow[])
        }
      } catch {
        if (!cancelled) {
          setActions([])
          setRuns([])
        }
      }
    }
    load()
    window.addEventListener('automation-status-refresh', load)
    const timer = window.setInterval(load, 3000)
    return () => {
      cancelled = true
      window.removeEventListener('automation-status-refresh', load)
      window.clearInterval(timer)
    }
  }, [])

  const state = useMemo(() => {
    const running = actions.filter(row => row.status === 'running')
    const pending = actions.filter(row => row.status === 'pending')
    const failed = actions.filter(row => row.status === 'failed')
    const latest = actions[0]
    const latestRun = runs[0]
    const runningRun = runs.find(row => row.status === 'running')
    if (runningRun) {
      const summary = runningRun.summary || {}
      const processed = summary.processed ?? 0
      const total = summary.actions_collected ?? 0
      return {
        tone: 'blue',
        title: '自动化周期运行中',
        detail: `阶段 ${summary.stage || 'running'} · 已处理 ${processed}/${total} · 成功 ${summary.executed ?? 0} · 失败 ${summary.failed ?? 0}`,
      }
    }
    if (running.length) {
      return {
        tone: 'blue',
        title: `自动化运行中 · ${running.length} 个动作`,
        detail: resultSummary(running[0]),
      }
    }
    if (pending.length) {
      return {
        tone: 'amber',
        title: `自动化排队中 · ${pending.length} 个动作`,
        detail: resultSummary(pending[0]),
      }
    }
    if (failed.length) {
      return {
        tone: 'red',
        title: `最近有 ${failed.length} 个动作失败`,
        detail: resultSummary(failed[0]),
      }
    }
    if (latest) {
      return {
        tone: 'slate',
        title: `最近动作：${statusLabel(latest.status)}`,
        detail: resultSummary(latest),
      }
    }
    if (latestRun) {
      const summary = latestRun.summary || {}
      const finishedAt = latestRun.finished_at ? new Date(latestRun.finished_at).getTime() : 0
      const isRecent = finishedAt > Date.now() - 10 * 60 * 1000
      if (!isRecent) return null
      return {
        tone: latestRun.status === 'ok' ? 'emerald' : 'amber',
        title: `最近自动化周期：${latestRun.status}`,
        detail: `已处理 ${summary.processed ?? summary.executed ?? 0}/${summary.actions_collected ?? 0} · 成功 ${summary.executed ?? 0} · 失败 ${summary.failed ?? 0}`,
      }
    }
    return null
  }, [actions, runs])

  async function retryLatestFailed() {
    const failed = actions.find(row => row.status === 'failed')
    if (!failed) return
    setBusy(true)
    try {
      await actionsApi.retry(failed.id)
      const rows = await actionsApi.list('?limit=20').catch(() => [])
      setActions(rows)
    } finally {
      setBusy(false)
    }
  }

  if (!state) return null
  const latestFailed = actions.find(row => row.status === 'failed')
  const toneClass =
    state.tone === 'blue'
      ? 'border-blue-500/40 bg-blue-950/80 text-blue-100'
      : state.tone === 'amber'
        ? 'border-amber-500/40 bg-amber-950/70 text-amber-100'
        : state.tone === 'red'
          ? 'border-rose-500/40 bg-rose-950/75 text-rose-100'
          : state.tone === 'emerald'
            ? 'border-emerald-500/30 bg-emerald-950/60 text-emerald-100'
            : 'border-slate-700 bg-slate-950/80 text-slate-200'

  return (
    <div className={`sticky top-0 z-40 mb-4 rounded-2xl border px-4 py-3 shadow-xl backdrop-blur ${toneClass}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-bold">{state.title}</div>
          <div className="mt-1 truncate text-xs opacity-80">{state.detail}</div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {latestFailed && (
            <button type="button" className="btn-secondary text-xs" disabled={busy} onClick={retryLatestFailed}>
              {busy ? '提交中...' : '重试失败动作'}
            </button>
          )}
          <a href="/settings/automation-cycle" className="btn-secondary text-xs">
            查看运行明细
          </a>
        </div>
      </div>
    </div>
  )
}
