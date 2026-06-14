'use client'

import {useState, useTransition} from 'react'
import {useRouter} from 'next/navigation'
import {automationCycleApi, submitAction} from '../lib/api'

export function DiscoveryPruneButton(){
  const router = useRouter()
  const [msg,setMsg] = useState('')
  const [err,setErr] = useState('')
  const [pending,startTransition] = useTransition()
  return <div className="flex flex-col items-start gap-2">
    <button className="btn-secondary" disabled={pending} onClick={()=>{
      setMsg(''); setErr('')
      startTransition(async()=>{
        try{
          await submitAction({action_type:'four_find.run', target_type:'four_find', target_id:'prune', reason:'手动清理低质量四找结果', payload:{operation:'prune'}}, false)
          const r:any = await automationCycleApi.run({include_default_actions:false, background:false})
          setMsg(`已提交清理动作：成功 ${r.succeeded ?? 0}，失败 ${r.failed ?? 0}`)
          router.refresh()
        }catch(e:any){ setErr(e.message || 'Prune failed') }
      })
    }}>{pending?'提交中...':'清理低质量发现'}</button>
    {msg&&<span className="text-xs text-emerald-300">{msg}</span>}
    {err&&<span className="text-xs text-rose-300">{err}</span>}
  </div>
}
