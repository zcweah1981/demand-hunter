'use client'

import {useState} from 'react'
import {useLang} from '../../lib/i18n'

export default function Login() {
  const {lang, setLang, t} = useLang()
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setErr('')
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({password}),
    })
    if (!res.ok) {
      setErr('Login failed')
      setLoading(false)
      return
    }
    const data = await res.json()
    localStorage.setItem('dh_token', data.token)
    document.cookie = `dh_token=${data.token}; path=/; max-age=2592000; samesite=lax`
    location.href = '/overview'
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <form onSubmit={submit} className="card w-full max-w-md space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-[0.25em] text-blue-300">Opportunity OS</div>
            <h1 className="mt-2 text-2xl font-bold text-white">{t('loginTitle')}</h1>
          </div>
          <div className="inline-flex shrink-0 rounded-xl border border-slate-700 bg-slate-900 p-1">
            <button type="button" className={`rounded-lg px-2 py-1 text-xs ${lang === 'zh' ? 'bg-blue-600 text-white' : 'text-slate-400'}`} onClick={() => setLang('zh')}>中文</button>
            <button type="button" className={`rounded-lg px-2 py-1 text-xs ${lang === 'en' ? 'bg-blue-600 text-white' : 'text-slate-400'}`} onClick={() => setLang('en')}>EN</button>
          </div>
        </div>
        <p className="text-sm text-slate-400">{t('loginSubtitle')}</p>
        <input className="input w-full" type="password" placeholder={t('password')} value={password} onChange={e => setPassword(e.target.value)} autoFocus />
        {err && <p className="text-sm text-red-400">{err}</p>}
        <button className="btn w-full" disabled={loading}>{loading ? t('loggingIn') : t('loginButton')}</button>
      </form>
    </main>
  )
}
