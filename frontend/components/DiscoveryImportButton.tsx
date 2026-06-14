'use client'

import {useState, useTransition} from 'react'
import {useRouter} from 'next/navigation'
import {submitAction} from '../lib/api'

export function DiscoveryImportButton({id,type}:{id:number;type:'expansion'|'competitor-keyword'}){
  const router = useRouter()
  const [error,setError] = useState('')
  const [pending,startTransition] = useTransition()
  const operation = type === 'expansion' ? 'import_expansion' : 'import_competitor_keyword'
  return <div className="flex flex-col gap-1">
    <button className="rounded bg-violet-600 px-2 py-1 text-xs text-white hover:bg-violet-500 disabled:opacity-50" disabled={pending} onClick={()=>{
      setError('')
      startTransition(async()=>{
        try{ await submitAction({action_type:'four_find.run', target_type:'four_find', target_id:id, reason:'手动导入四找结果', payload:{operation}}); router.refresh() }
        catch(err:any){ setError(err.message || 'Import failed') }
      })
    }}>{pending?'提交中...':'入库'}</button>
    {error&&<span className="text-[10px] text-rose-300">{error}</span>}
  </div>
}
