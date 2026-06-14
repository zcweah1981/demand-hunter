'use client'

import {useState, useTransition} from 'react'
import {useRouter} from 'next/navigation'
import {automationCycleApi, submitAction} from '../lib/api'

export function DiscoveryDomainForm(){
  const router = useRouter()
  const [domain,setDomain] = useState('')
  const [results,setResults] = useState<any>(null)
  const [error,setError] = useState('')
  const [pending,startTransition] = useTransition()

  async function submit(e:React.FormEvent){
    e.preventDefault()
    if(!domain.trim()) return
    setError(''); setResults(null)
    startTransition(async()=>{
      try{
        const clean = domain.replace(/^https?:\/\//,'').replace(/^www\./,'').split('/')[0]
        await submitAction({action_type:'four_find.run', target_type:'four_find', target_id:'site_keywords', reason:'手动四找站找词', payload:{operation:'site_keywords', domain:clean}}, false)
        await submitAction({action_type:'four_find.run', target_type:'four_find', target_id:'similar_sites', reason:'手动四找站找站', payload:{operation:'similar_sites', domain:clean}}, false)
        const run:any = await automationCycleApi.run({include_default_actions:false, background:false})
        setResults({summary: run})
        router.refresh()
      }catch(err:any){ setError(err.message || 'Discovery failed') }
    })
  }

  return <form onSubmit={submit} className="mt-5 space-y-4">
    <div className="flex flex-col gap-3 sm:flex-row">
      <input className="input flex-1" value={domain} onChange={e=>setDomain(e.target.value)} placeholder="example.com" />
      <button className="btn" disabled={pending || !domain.trim()}>{pending?'提交并运行中...':'运行站点线索'}</button>
    </div>
    {error&&<p className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p>}
    {results&&<div className="grid gap-3 text-sm md:grid-cols-2">
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b className="text-cyan-300">动作状态</b><div className="mt-1 text-slate-400">已提交到统一自动化周期。</div></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b className="text-emerald-300">运行进度</b><div className="mt-1 text-slate-400">顶部状态栏和运行明细会显示处理数量、异常和结果。</div></div>
    </div>}
  </form>
}
