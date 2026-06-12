'use client'

import {useEffect, useMemo, useState} from 'react'
import {api, Keyword} from '../lib/api'
import {KeywordDetailContent} from './KeywordDetailContent'

type KeywordAsset = Keyword & {
  lifecycle: string
  lifecycleLabel: string
  sourceModel: string
  sourceModelRaw: string
  inputObject: string
  totalScore: number
  lastAnalyzedAt: string
  opportunityStatus: string
  nextStep: string
}

const STATUS_OPTIONS = [
  {value: 'all', label: '全部'},
  {value: 'pending_analysis', label: '待分析'},
  {value: 'needs_evidence', label: '待补证据'},
  {value: 'monitoring', label: '持续监控'},
  {value: 'opportunity_created', label: '已生成机会'},
  {value: 'filtered', label: '已过滤'},
]

const SORT_OPTIONS = [
  {value: 'score_desc', label: '总评分高到低'},
  {value: 'recent_desc', label: '最近分析时间'},
  {value: 'created_desc', label: '产生时间'},
  {value: 'query_asc', label: '关键词 A-Z'},
]

const PAGE_SIZE_OPTIONS = [25, 50, 100]

const SOURCE_LABELS: Record<string, string> = {
  'collector:google_suggest': 'Google Suggest',
  'collector:alternatives': '替代品/竞品',
  'collector:hot_topic': '热点/早期信号',
  'collector:domain_web': 'Domain Web',
  'collector:sitemap': 'Sitemap',
  'collector:advanced_search': 'SERP Search',
  'collector:short_tail_rewrite': 'Short Tail Rewrite',
  root_combo: 'Root Combo',
  'four_find:business_modifier': '四找·商业修饰',
  'four_find:seed': '四找·种子词',
  'four_find:expansion': '四找·扩展词',
  keyword_engine: '关键词引擎',
  manual: '人工导入',
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function text(value: unknown) {
  return typeof value === 'string' && value.trim() ? value.trim() : ''
}

function scoreValue(raw: unknown) {
  const n = Number(raw)
  if (!Number.isFinite(n)) return 0
  if (n <= 1) return n * 100
  if (n > 100) return Math.min(100, n / 100)
  return n
}

function fmtScore(raw: number) {
  return raw > 0 ? raw.toFixed(1) : '待评分'
}

function fmtDate(raw?: string | null) {
  if (!raw) return '未分析'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return raw
  return d.toLocaleString('zh-CN', {year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit'})
}

function sourceLabel(raw: string) {
  return SOURCE_LABELS[raw] || raw || '未记录'
}

function inputObject(keyword: Keyword) {
  const root = keyword.root_terms as unknown
  if (Array.isArray(root) && root.length) return root.slice(0, 2).join(' / ')
  const meta = asRecord(root)
  const input = text(meta.input_ref) || text(meta.input) || text(meta.seed) || text(meta.source_domain)
  return input || keyword.query
}

function lifecycleFor(keyword: Keyword) {
  if (['reject', 'block'].includes(keyword.status)) return {value: 'filtered', label: '已过滤'}
  if (keyword.status === 'action') return {value: 'opportunity_created', label: '已生成机会'}
  if (keyword.status === 'watch') return {value: 'monitoring', label: '持续监控'}
  if (keyword.status === 'adopted') return {value: 'needs_evidence', label: '待补证据'}
  return {value: 'pending_analysis', label: '待分析'}
}

function nextStepFor(asset: Pick<KeywordAsset, 'lifecycle' | 'opportunityStatus'>) {
  if (asset.lifecycle === 'opportunity_created') return '查看机会推进'
  if (asset.lifecycle === 'needs_evidence') return '等待补证据任务'
  if (asset.lifecycle === 'monitoring') return '持续自动监控'
  if (asset.lifecycle === 'filtered') return '已暂停'
  return '等待自动搜索分析'
}

function toAsset(keyword: Keyword): KeywordAsset {
  const lifecycle = lifecycleFor(keyword)
  const meta = asRecord(keyword.root_terms as unknown)
  const sourceModelRaw = text(meta.source_model) || keyword.source
  const opportunityStatus = keyword.status === 'action' ? '已生成机会' : '未生成'
  const totalScore = scoreValue(keyword.score)
  return {
    ...keyword,
    lifecycle: lifecycle.value,
    lifecycleLabel: lifecycle.label,
    sourceModel: sourceLabel(sourceModelRaw),
    sourceModelRaw,
    inputObject: inputObject(keyword),
    totalScore,
    lastAnalyzedAt: text(meta.last_analyzed_at) || text(meta.serp_analyzed_at) || '',
    opportunityStatus,
    nextStep: nextStepFor({lifecycle: lifecycle.value, opportunityStatus}),
  }
}

function KeywordDrawer({keywordId, onClose}: {keywordId: number; onClose: () => void}) {
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let live = true
    setData(null)
    setError('')
    api<any>(`/api/keywords/${keywordId}`)
      .then(next => { if (live) setData(next) })
      .catch(err => { if (live) setError(err instanceof Error ? err.message : '详情加载失败') })
    return () => { live = false }
  }, [keywordId])

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50">
      <button className="absolute inset-0 bg-black/70" onClick={onClose} aria-label="关闭关键词详情" />
      <aside className="absolute right-0 top-0 h-full w-full max-w-7xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-5 shadow-2xl">
        <div className="mb-5 flex items-start justify-between gap-3">
          <div>
            <div className="text-xs uppercase tracking-[0.25em] text-blue-300">Keyword Drawer</div>
            <h2 className="mt-1 text-2xl font-bold text-white">关键词详情</h2>
            <p className="mt-1 text-sm text-slate-400">在当前关键词库页面内查看来源、评分、证据和后续自动动作。</p>
          </div>
          <button className="btn-secondary" onClick={onClose}>关闭</button>
        </div>
        {error && <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">{error}</div>}
        {!error && !data && <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-400">正在加载关键词详情...</div>}
        {data && <KeywordDetailContent data={data} compact />}
      </aside>
    </div>
  )
}

function StatusBadge({asset}: {asset: KeywordAsset}) {
  const tones: Record<string, string> = {
    pending_analysis: 'border-blue-500/40 bg-blue-500/10 text-blue-200',
    needs_evidence: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
    monitoring: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
    opportunity_created: 'border-purple-500/40 bg-purple-500/10 text-purple-200',
    filtered: 'border-rose-500/40 bg-rose-500/10 text-rose-200',
  }
  return <span className={`inline-flex rounded-full border px-2 py-1 text-xs ${tones[asset.lifecycle] || 'border-slate-700 text-slate-300'}`}>{asset.lifecycleLabel}</span>
}

export function KeywordLibraryPage({rows}: {rows: Keyword[]}) {
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [status, setStatus] = useState('all')
  const [source, setSource] = useState('all')
  const [opportunity, setOpportunity] = useState('all')
  const [sort, setSort] = useState('score_desc')
  const [pageSize, setPageSize] = useState(25)
  const [page, setPage] = useState(1)

  const assets = useMemo(() => rows.map(toAsset), [rows])
  const sourceOptions = useMemo(() => {
    const values = Array.from(new Set(assets.map(asset => asset.sourceModelRaw).filter(Boolean)))
    return values.map(value => ({value, label: sourceLabel(value)})).sort((a, b) => a.label.localeCompare(b.label))
  }, [assets])

  const filtered = useMemo(() => {
    const next = assets.filter(asset => {
      if (status !== 'all' && asset.lifecycle !== status) return false
      if (source !== 'all' && asset.sourceModelRaw !== source) return false
      if (opportunity === 'with' && asset.opportunityStatus !== '已生成机会') return false
      if (opportunity === 'without' && asset.opportunityStatus === '已生成机会') return false
      return true
    })
    return [...next].sort((a, b) => {
      if (sort === 'recent_desc') return new Date(b.lastAnalyzedAt || b.created_at).getTime() - new Date(a.lastAnalyzedAt || a.created_at).getTime()
      if (sort === 'created_desc') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      if (sort === 'query_asc') return a.query.localeCompare(b.query)
      return b.totalScore - a.totalScore
    })
  }, [assets, opportunity, sort, source, status])

  useEffect(() => {
    setPage(1)
  }, [status, source, opportunity, sort, pageSize])

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const start = filtered.length ? (safePage - 1) * pageSize + 1 : 0
  const end = Math.min(safePage * pageSize, filtered.length)
  const pageRows = filtered.slice((safePage - 1) * pageSize, safePage * pageSize)
  const counts = {
    total: assets.length,
    pending: assets.filter(k => k.lifecycle === 'pending_analysis').length,
    evidence: assets.filter(k => k.lifecycle === 'needs_evidence').length,
    opportunities: assets.filter(k => k.lifecycle === 'opportunity_created').length,
  }

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-6 shadow-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Keyword Asset Library</p>
        <h1 className="mt-2 text-3xl font-black text-white">关键词库</h1>
        <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-300">
          这里只管理已经进入关键词库的搜索资产。发现和候选筛选留在线索模型库与线索池；关键词库负责持续搜索分析、证据补齐和机会生成。
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <div className="rounded-xl border border-slate-700/60 bg-slate-950/70 px-4 py-3">
            <div className="text-xs text-slate-400">入库关键词</div>
            <div className="mt-1 text-2xl font-bold text-white">{counts.total}</div>
          </div>
          <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 px-4 py-3">
            <div className="text-xs text-slate-400">待分析</div>
            <div className="mt-1 text-2xl font-bold text-blue-200">{counts.pending}</div>
          </div>
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
            <div className="text-xs text-slate-400">待补证据</div>
            <div className="mt-1 text-2xl font-bold text-amber-200">{counts.evidence}</div>
          </div>
          <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 px-4 py-3">
            <div className="text-xs text-slate-400">已生成机会</div>
            <div className="mt-1 text-2xl font-bold text-purple-200">{counts.opportunities}</div>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-white">入库关键词明细</h2>
            <p className="mt-1 text-sm text-slate-400">按状态、来源模型、机会状态筛选；点击关键词查看评分、来源链路、搜索分析和证据。</p>
          </div>
          <div className="text-sm text-slate-400">显示 {start}-{end} / {filtered.length}，总计 {assets.length}</div>
        </div>

        <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
          <div className="grid gap-3 lg:grid-cols-4">
            <label className="text-sm text-slate-300">
              <span className="mb-1 block">分类</span>
              <select className="input w-full" value={status} onChange={event => setStatus(event.target.value)}>
                {STATUS_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            <label className="text-sm text-slate-300">
              <span className="mb-1 block">来源模型</span>
              <select className="input w-full" value={source} onChange={event => setSource(event.target.value)}>
                <option value="all">全部</option>
                {sourceOptions.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            <label className="text-sm text-slate-300">
              <span className="mb-1 block">机会状态</span>
              <select className="input w-full" value={opportunity} onChange={event => setOpportunity(event.target.value)}>
                <option value="all">全部</option>
                <option value="with">已生成机会</option>
                <option value="without">未生成机会</option>
              </select>
            </label>
            <label className="text-sm text-slate-300">
              <span className="mb-1 block">排序</span>
              <select className="input w-full" value={sort} onChange={event => setSort(event.target.value)}>
                {SORT_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
          </div>
        </div>

        <div className="mt-5 overflow-x-auto rounded-2xl border border-slate-800">
          <table className="w-full min-w-[1040px] text-sm">
            <thead className="table-head">
              <tr>
                <th className="py-3 text-left">关键词</th>
                <th className="py-3 text-left">状态</th>
                <th className="py-3 text-left">来源模型</th>
                <th className="py-3 text-left">输入对象</th>
                <th className="py-3 text-left">总评分</th>
                <th className="py-3 text-left">最近分析时间</th>
                <th className="py-3 text-left">机会状态</th>
                <th className="py-3 text-left">下一步</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map(asset => (
                <tr className="border-t border-slate-800 transition hover:bg-slate-800/30" key={asset.id}>
                  <td className="max-w-[260px] py-3 font-medium">
                    <button className="truncate text-left text-blue-200 hover:text-blue-100 hover:underline" type="button" onClick={() => setSelectedId(asset.id)}>
                      {asset.query}
                    </button>
                  </td>
                  <td className="py-3"><StatusBadge asset={asset} /></td>
                  <td className="max-w-[150px] truncate py-3 text-slate-300" title={asset.sourceModel}>{asset.sourceModel}</td>
                  <td className="max-w-[220px] truncate py-3 text-slate-400" title={asset.inputObject}>{asset.inputObject}</td>
                  <td className="py-3 font-mono font-semibold text-slate-100">{fmtScore(asset.totalScore)}</td>
                  <td className="max-w-[160px] py-3 text-slate-400">{fmtDate(asset.lastAnalyzedAt)}</td>
                  <td className="py-3 text-slate-300">{asset.opportunityStatus}</td>
                  <td className="max-w-[180px] py-3 text-slate-300">{asset.nextStep}</td>
                </tr>
              ))}
              {!pageRows.length && (
                <tr>
                  <td className="py-10 text-center text-slate-500" colSpan={8}>当前筛选条件下暂无入库关键词。</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
          <div className="text-sm text-slate-500">第 {safePage} / {totalPages} 页</div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              每页
              <select className="input w-24" value={pageSize} onChange={event => setPageSize(Number(event.target.value))}>
                {PAGE_SIZE_OPTIONS.map(size => <option key={size} value={size}>{size}</option>)}
              </select>
            </label>
            <button className="btn-secondary" disabled={safePage <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>上一页</button>
            <button className="btn-secondary" disabled={safePage >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))}>下一页</button>
          </div>
        </div>
      </section>

      {selectedId !== null && <KeywordDrawer keywordId={selectedId} onClose={() => setSelectedId(null)} />}
    </div>
  )
}
