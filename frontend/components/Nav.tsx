'use client'

import Link from 'next/link'
import {LogoutButton} from './LogoutButton'
import {useLang} from '../lib/i18n'

const items = [
  ['/overview', 'overview'],
  ['/discovery', 'discovery'],
  ['/', 'dashboard'],
  ['/review', 'review'],
  ['/cards', 'cards'],
  ['/keywords', 'keywords'],
  ['/roots', 'roots'],
  ['/runs', 'runs'],
  ['/settings', 'settings'],
]

export function Nav() {
  const {lang, setLang, t} = useLang()
  return (
    <aside className="border-b border-slate-800 bg-slate-950/95 p-4 backdrop-blur lg:sticky lg:top-0 lg:min-h-screen lg:w-72 lg:shrink-0 lg:border-b-0 lg:border-r lg:p-5">
      <div className="flex flex-wrap items-start justify-between gap-4 lg:block">
        <div className="min-w-0">
          <div className="text-xl font-black text-white lg:text-2xl">Demand Hunter</div>
          <div className="mt-1 text-xs uppercase tracking-[0.25em] text-blue-300">Opportunity OS</div>
        </div>
        <div className="inline-flex shrink-0 rounded-xl border border-slate-700 bg-slate-900 p-1 lg:mt-4">
          <button className={`rounded-lg px-3 py-1 text-xs ${lang === 'zh' ? 'bg-blue-600 text-white' : 'text-slate-400'}`} onClick={() => setLang('zh')}>中文</button>
          <button className={`rounded-lg px-3 py-1 text-xs ${lang === 'en' ? 'bg-blue-600 text-white' : 'text-slate-400'}`} onClick={() => setLang('en')}>EN</button>
        </div>
      </div>

      <nav className="mt-4 flex gap-2 overflow-x-auto pb-1 lg:mt-8 lg:block lg:space-y-2 lg:overflow-visible lg:pb-0">
        {items.map(([href, key]) => (
          <Link className="shrink-0 rounded-xl px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white lg:block" href={href} key={href}>
            {t(key)}
          </Link>
        ))}
      </nav>

      <div className="mt-5 hidden rounded-2xl border border-slate-800 bg-slate-900/70 p-4 text-xs text-slate-400 lg:block">
        <div className="mb-2 font-semibold text-slate-200">{t('qualityFormula')}</div>
        <p>{t('formula')}</p>
      </div>
      <div className="mt-4 lg:mt-8"><LogoutButton /></div>
    </aside>
  )
}
