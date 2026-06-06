'use client'

import {useState, useTransition} from 'react'
import {useRouter} from 'next/navigation'
import {api} from '../lib/api'

export function DiscoveryImportButton({id,type}:{id:number;type:'expansion'|'competitor-keyword'}){
  const router = useRouter()
  const [error,setError] = useState('')
  const [pending,startTransition] = useTransition()
  const path = type === 'expansion' ? `/api/discovery/import-expansion/${id}` : `/api/discovery/import-competitor-keyword/${id}`
  return <div className="flex flex-col gap-1">
    <button className="rounded bg-violet-600 px-2 py-1 text-xs text-white hover:bg-violet-500 disabled:opacity-50" disabled={pending} onClick={()=>{
      setError('')
      startTransition(async()=>{
        try{ await api(path,{method:'POST'}); router.refresh() }
        catch(err:any){ setError(err.message || 'Import failed') }
      })
    }}>{pending?'Importing...':'Import'}</button>
    {error&&<span className="text-[10px] text-rose-300">{error}</span>}
  </div>
}
