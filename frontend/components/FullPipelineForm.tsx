'use client'

import {useState, useTransition} from 'react'
import {useRouter} from 'next/navigation'
import {automationCycleApi, submitAction} from '../lib/api'

export function FullPipelineForm(){
  const router = useRouter()
  const [seed,setSeed] = useState('')
  const [depth,setDepth] = useState(2)
  const [summary,setSummary] = useState<any>(null)
  const [error,setError] = useState('')
  const [pending,startTransition] = useTransition()

  async function submit(e:React.FormEvent){
    e.preventDefault()
    if(!seed.trim()) return
    setError(''); setSummary(null)
    startTransition(async()=>{
      try{
        await submitAction({action_type:'four_find.run', target_type:'four_find', target_id:'run_and_import', reason:'手动完整四找流水线', payload:{operation:'run_and_import', seed, depth, import_limit:12}}, false)
        const data = await automationCycleApi.run({include_default_actions:false, background:false})
        setSummary(data)
        router.refresh()
      }catch(err:any){ setError(err.message || 'Pipeline failed') }
    })
  }

  return <form onSubmit={submit} className="mt-5 space-y-4">
    <div className="grid gap-3 md:grid-cols-[1fr_120px_auto]">
      <input className="input" value={seed} onChange={e=>setSeed(e.target.value)} placeholder="chargeback evidence template" />
      <input className="input" type="number" min={1} max={5} value={depth} onChange={e=>setDepth(Number(e.target.value)||2)} />
      <button className="btn" disabled={pending || !seed.trim()}>{pending?'提交并运行中...':'运行并入库'}</button>
    </div>
    {error&&<p className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p>}
    {summary&&<div className="grid gap-3 text-sm md:grid-cols-5">
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b>本轮动作</b><div className="mt-1 text-slate-400">{summary.executed ?? 0}</div></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b>成功</b><div className="mt-1 text-slate-400">{summary.succeeded ?? 0}</div></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b>失败</b><div className="mt-1 text-slate-400">{summary.failed ?? 0}</div></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b>后续动作</b><div className="mt-1 text-slate-400">{summary.next_actions_created ?? 0}</div></div>
      <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/20 p-4"><b>运行明细</b><div className="mt-1 text-emerald-300">查看顶部状态栏入口</div></div>
    </div>}
  </form>
}
