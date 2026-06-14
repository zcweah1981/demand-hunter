'use client'

import {useState, useTransition} from 'react'
import {useRouter} from 'next/navigation'
import {automationCycleApi, submitAction} from '../lib/api'

export function DiscoverySeedForm(){
  const router = useRouter()
  const [seed,setSeed] = useState('')
  const [results,setResults] = useState<any>(null)
  const [error,setError] = useState('')
  const [pending,startTransition] = useTransition()

  async function submit(e:React.FormEvent){
    e.preventDefault()
    if(!seed.trim()) return
    setError(''); setResults(null)
    startTransition(async()=>{
      try{
        await submitAction({action_type:'four_find.run', target_type:'four_find', target_id:'expand', reason:'手动四找词找词', payload:{operation:'expand', seed}}, false)
        await submitAction({action_type:'four_find.run', target_type:'four_find', target_id:'find_sites', reason:'手动四找词找站', payload:{operation:'find_sites', seed}}, false)
        const run:any = await automationCycleApi.run({include_default_actions:false, background:false})
        setResults({summary: run})
        router.refresh()
      }catch(err:any){ setError(err.message || 'Discovery failed') }
    })
  }

  return <form onSubmit={submit} className="mt-5 space-y-4">
    <div className="flex flex-col gap-3 sm:flex-row">
      <input className="input flex-1" value={seed} onChange={e=>setSeed(e.target.value)} placeholder="invoice late fee calculator" />
      <button className="btn" disabled={pending || !seed.trim()}>{pending?'提交并运行中...':'运行关键词线索'}</button>
    </div>
    {error&&<p className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p>}
    {results&&<div className="grid gap-3 text-sm md:grid-cols-2">
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b className="text-violet-300">动作状态</b><div className="mt-1 text-slate-400">已提交到统一自动化周期。</div></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b className="text-blue-300">运行进度</b><div className="mt-1 text-slate-400">顶部状态栏和运行明细会显示处理数量、异常和结果。</div></div>
    </div>}
  </form>
}
