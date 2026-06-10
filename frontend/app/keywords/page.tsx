import Link from 'next/link'
import {api, Keyword} from '../../lib/api'
import {DiscoverButton} from '../../components/Actions'
import {I18nText} from '../../components/I18nText'

/* ── helpers ── */

const STATUS_MAP: Record<string, {label: string; tone: string}> = {
  adopted:  {label: '已采纳',  tone: 'border-purple-500/40 bg-purple-500/10 text-purple-200'},
  action:   {label: '待行动',  tone: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200'},
  watch:    {label: '观察中',  tone: 'border-blue-500/40 bg-blue-500/10 text-blue-200'},
  reject:   {label: '已排除',  tone: 'border-amber-500/40 bg-amber-500/10 text-amber-200'},
  block:    {label: '已屏蔽',  tone: 'border-rose-500/40 bg-rose-500/10 text-rose-200'},
  new:      {label: '新发现',  tone: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200'},
}

function statusBadge(status: string) {
  const s = STATUS_MAP[status] || {label: status, tone: 'border-slate-600 bg-slate-800 text-slate-300'}
  return <span className={`inline-block rounded border px-2 py-0.5 text-xs ${s.tone}`}>{s.label}</span>
}

function intentLabel(raw: string) {
  if (!raw || raw === 'unknown') return '待分析'
  if (raw.startsWith('search_demand')) return '有搜索需求'
  if (raw.startsWith('evidence_for_card:')) return `补充证据 #${raw.split(':')[1]}`
  if (raw.startsWith('duplicate_card:')) return `关联卡片 #${raw.split(':')[1]}`
  return raw
}

function sourceLabel(raw: string) {
  if (!raw) return '—'
  const map: Record<string, string> = {
    'collector:alternatives': '竞品替代分析',
    'collector:hot_topic': '热门话题',
    'collector:domain_web': '网站抓取',
    'collector:advanced_search': '深度搜索',
    'collector:short_tail_rewrite': '短词重写',
    'four_find:business_modifier': '四找·商业修饰',
    'four_find:seed': '四找·种子词',
    'four_find:expansion': '四找·扩展词',
    'keyword_engine': '关键词引擎',
    'manual': '手动添加',
  }
  return map[raw] || raw
}

function scoreColor(score: number) {
  if (score >= 78) return 'text-emerald-300'
  if (score >= 72) return 'text-blue-300'
  if (score >= 65) return 'text-amber-300'
  return 'text-slate-400'
}

/* ── page ── */

export default async function Page() {
  const rows = await api<Keyword[]>('/api/keywords')

  const counts = {
    total: rows.length,
    adopted: rows.filter(k => k.status === 'adopted').length,
    action: rows.filter(k => k.status === 'action').length,
    watch: rows.filter(k => k.status === 'watch').length,
    reject: rows.filter(k => k.status === 'reject').length,
  }

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-6 shadow-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Keyword Pipeline</p>
        <h1 className="mt-2 text-3xl font-black text-white">
          <I18nText zh="关键词库" en="Keywords"/>
        </h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-300">
          <I18nText
            zh="关键词是系统发现机会的起点。每个关键词代表一个真实用户可能搜索的词——系统用它去 Google 搜索，分析搜索结果中竞争对手的弱点，最终判断这个方向是否值得做产品。"
            en="Keywords are the starting point for opportunity discovery. Each keyword represents a real user search query — the system uses it to search Google, analyze competitor weaknesses in search results, and ultimately decide whether this direction is worth building a product."
          />
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 px-4 py-2">
            <div className="text-xs text-slate-400">已采纳</div>
            <div className="text-lg font-bold text-purple-300">{counts.adopted}</div>
          </div>
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-2">
            <div className="text-xs text-slate-400">待行动</div>
            <div className="text-lg font-bold text-emerald-300">{counts.action}</div>
          </div>
          <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 px-4 py-2">
            <div className="text-xs text-slate-400">观察中</div>
            <div className="text-lg font-bold text-blue-300">{counts.watch}</div>
          </div>
          <div className="rounded-xl border border-slate-600/30 bg-slate-800/30 px-4 py-2">
            <div className="text-xs text-slate-400">总计</div>
            <div className="text-lg font-bold text-slate-200">{counts.total}</div>
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="panel">
        <h2 className="text-lg font-bold">
          <I18nText zh="🔑 关键词怎么工作？" en="🔑 How Keywords Work"/>
        </h2>
        <div className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
          <div className="rounded-xl border border-slate-700/50 bg-slate-900/50 p-4">
            <div className="font-semibold text-blue-200">
              <I18nText zh="1️⃣ 发现关键词" en="1️⃣ Discover"/>
            </div>
            <p className="mt-1 text-slate-400">
              <I18nText
                zh="系统从竞品分析、热门话题、四找引擎等渠道自动发现搜索词，也可以手动添加。"
                en="System discovers search terms from competitor analysis, hot topics, four-find engine, etc. You can also add manually."
              />
            </p>
          </div>
          <div className="rounded-xl border border-slate-700/50 bg-slate-900/50 p-4">
            <div className="font-semibold text-blue-200">
              <I18nText zh="2️⃣ 搜索分析" en="2️⃣ Search & Analyze"/>
            </div>
            <p className="mt-1 text-slate-400">
              <I18nText
                zh="用关键词去 Google 搜索，看搜索结果（SERP）里竞争对手做得好不好，找到他们没覆盖的弱点。"
                en="Search Google with the keyword, check if competitors cover it well, find weaknesses they missed."
              />
            </p>
          </div>
          <div className="rounded-xl border border-slate-700/50 bg-slate-900/50 p-4">
            <div className="font-semibold text-blue-200">
              <I18nText zh="3️⃣ 产出机会卡" en="3️⃣ Generate Opportunity"/>
            </div>
            <p className="mt-1 text-slate-400">
              <I18nText
                zh="结合搜索分析和需求信号，生成机会卡——告诉你这个方向值不值得做、怎么做、怎么赚钱。"
                en="Combine search analysis and demand signals into an opportunity card — telling you if this direction is worth pursuing, how, and how to monetize."
              />
            </p>
          </div>
        </div>
      </section>

      {/* ── Actions ── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-bold">
          <I18nText zh="全部关键词" en="All Keywords"/>
          <span className="ml-2 text-sm font-normal text-slate-500">{rows.length}</span>
        </h2>
        <DiscoverButton/>
      </div>

      {/* ── Table ── */}
      <div className="panel">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="table-head">
              <tr>
                <th className="whitespace-nowrap py-3 text-left">🔍 <I18nText zh="搜索词" en="Keyword"/></th>
                <th className="whitespace-nowrap py-3 text-left"><I18nText zh="状态" en="Status"/></th>
                <th className="whitespace-nowrap py-3 text-left"><I18nText zh="意图" en="Intent"/></th>
                <th className="whitespace-nowrap py-3 text-left">⭐ <I18nText zh="评分" en="Score"/></th>
                <th className="whitespace-nowrap py-3 text-left"><I18nText zh="来源" en="Source"/></th>
              </tr>
            </thead>
            <tbody>
              {rows.map(k => (
                <tr className="border-t border-slate-800 transition hover:bg-slate-800/30" key={k.id}>
                  <td className="max-w-[300px] truncate py-3 font-medium">
                    <Link className="text-blue-200 hover:text-blue-100 hover:underline" href={`/keywords/${k.id}`}>
                      {k.query}
                    </Link>
                  </td>
                  <td className="py-3">{statusBadge(k.status)}</td>
                  <td className="max-w-[140px] truncate py-3 text-xs text-slate-400" title={k.intent}>
                    {intentLabel(k.intent)}
                  </td>
                  <td className={`py-3 font-mono text-sm ${scoreColor(k.score)}`}>
                    {k.score.toFixed(1)}
                  </td>
                  <td className="max-w-[130px] truncate py-3 text-xs text-slate-500" title={k.source}>
                    {sourceLabel(k.source)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
