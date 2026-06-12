'use client'

import Link from 'next/link'
import {useEffect, useState} from 'react'
import {usePathname} from 'next/navigation'
import {LogoutButton} from './LogoutButton'
import {useLang} from '../lib/i18n'

const discoveryItems = [
  ['/discovery/overview', '发现总览'],
  ['/collectors/sources', '线索模型库'],
  ['/discovery/entries', '线索池'],
  ['/keywords', '关键词库'],
]

const evidenceItems = [
  ['/evidence', '证据总览'],
  ['/evidence/models', '证据模型'],
  ['/evidence/tasks', '补证任务'],
  ['/evidence/timeline', '证据时间线'],
  ['/evidence/watch', '监控对象'],
  ['/evidence/derived', '证据新词'],
  ['/evidence/repairs', '异常修复'],
]

const hunterItems = [
  ['/hunter', '验证总览'],
  ['/hunter/opportunities', '可行动机会'],
  ['/hunter/progress', '机会推进'],
]

const settingsItems = [
  ['/settings/api-keys', 'API Key 管理中心'],
  ['/settings/search', '搜索总控'],
  ['/settings/searxng', 'SearXNG'],
  ['/settings/llm', 'LLM'],
  ['/settings/automation-cycle', '自动运行周期'],
  ['/settings/automation', '自动化'],
  ['/settings/quality', '质量控制'],
  ['/settings/security', '安全'],
]

export function Nav() {
  const {lang, setLang, t} = useLang()
  const pathname = usePathname()
  const [open, setOpen] = useState<'discovery'|'evidence'|'hunter'|'settings'|null>(null)

  useEffect(() => {
    if (pathname === '/' || pathname.startsWith('/hunter') || pathname.startsWith('/review') || pathname.startsWith('/cards')) setOpen('hunter')
    else if (pathname.startsWith('/evidence')) setOpen('evidence')
    else if (pathname.startsWith('/discovery') || pathname.startsWith('/keywords') || pathname.startsWith('/collectors')) setOpen('discovery')
    else if (pathname.startsWith('/settings')) setOpen('settings')
  }, [pathname])

  const linkClass = (href:string) => {
    const active = href === '/' ? pathname === '/' : pathname.startsWith(href)
    return `block rounded-xl px-3 py-2 text-sm no-underline transition ${active ? 'bg-blue-600/20 text-blue-100 ring-1 ring-blue-500/40' : 'text-slate-300 hover:bg-slate-800 hover:text-white'}`
  }
  const childClass = (href:string) => {
    const active = href === '/hunter' ? (pathname === '/' || pathname === '/hunter') : pathname.startsWith(href)
    return `block rounded-xl px-3 py-2 text-sm no-underline transition ${active ? 'bg-blue-600/20 text-blue-100' : 'text-slate-400 hover:bg-slate-800 hover:text-white'}`
  }
  const sectionButton = (id:'discovery'|'evidence'|'hunter'|'settings', label:string) => (
    <button
      type="button"
      onClick={() => setOpen(open === id ? null : id)}
      className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm transition ${open===id?'bg-slate-800 text-white':'text-slate-300 hover:bg-slate-800 hover:text-white'}`}
    >
      <span>{label}</span><span className="text-xs text-slate-500">{open===id?'▾':'▸'}</span>
    </button>
  )

  return (
    <aside className="border-b border-slate-800 bg-slate-950/95 p-4 backdrop-blur md:sticky md:top-0 md:min-h-screen md:w-72 md:shrink-0 md:border-b-0 md:border-r md:p-5">
      <div className="flex flex-wrap items-start justify-between gap-4 md:block">
        <div className="min-w-0">
          <div className="text-xl font-black text-white md:text-2xl">Demand Hunter</div>
          <div className="mt-1 text-xs uppercase tracking-[0.25em] text-blue-300">Opportunity OS</div>
        </div>
        <div className="inline-flex shrink-0 rounded-xl border border-slate-700 bg-slate-900 p-1 md:mt-4">
          <button className={`rounded-lg px-3 py-1 text-xs ${lang === 'zh' ? 'bg-blue-600 text-white' : 'text-slate-400'}`} onClick={() => setLang('zh')}>中文</button>
          <button className={`rounded-lg px-3 py-1 text-xs ${lang === 'en' ? 'bg-blue-600 text-white' : 'text-slate-400'}`} onClick={() => setLang('en')}>EN</button>
        </div>
      </div>

      <nav className="mt-4 flex gap-2 overflow-x-auto pb-1 md:mt-8 md:block md:space-y-2 md:overflow-visible md:pb-0">
        <div className="min-w-[170px] shrink-0 md:min-w-0">
          {sectionButton('discovery', '机会发现')}
          {open==='discovery'&&<div className="mt-2 space-y-1 rounded-2xl border border-slate-800 bg-slate-900/50 p-2">
            {discoveryItems.map(([href, label]) => <Link prefetch={false} key={href} className={childClass(href)} href={href}>{label}</Link>)}
          </div>}
        </div>
        <div className="min-w-[170px] shrink-0 md:min-w-0">
          {sectionButton('evidence', '证据系统')}
          {open==='evidence'&&<div className="mt-2 space-y-1 rounded-2xl border border-slate-800 bg-slate-900/50 p-2">
            {evidenceItems.map(([href, label]) => <Link prefetch={false} key={href} className={childClass(href)} href={href}>{label}</Link>)}
          </div>}
        </div>
        <div className="min-w-[170px] shrink-0 md:min-w-0">
          {sectionButton('hunter', '机会猎手')}
          {open==='hunter'&&<div className="mt-2 space-y-1 rounded-2xl border border-slate-800 bg-slate-900/50 p-2">
            {hunterItems.map(([href, label]) => <Link prefetch={false} key={href} className={childClass(href)} href={href}>{label}</Link>)}
          </div>}
        </div>
        <div className="min-w-[170px] shrink-0 md:min-w-0">
          {sectionButton('settings', t('settings'))}
          {open==='settings'&&<div className="mt-2 space-y-1 rounded-2xl border border-slate-800 bg-slate-900/50 p-2">
            {settingsItems.map(([href, label]) => <Link prefetch={false} key={href} className={childClass(href)} href={href}>{label}</Link>)}
          </div>}
        </div>
      </nav>

      <div className="mt-4 md:mt-8"><LogoutButton /></div>
    </aside>
  )
}
