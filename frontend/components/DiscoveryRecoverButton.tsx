'use client'

import {useState, useTransition} from 'react'
import {useRouter} from 'next/navigation'
import {api} from '../lib/api'
import {pollJob} from '../lib/jobPoll'

export function DiscoveryRecoverButton(){
  const router = useRouter()
  const [msg,setMsg] = useState('')
  const [err,setErr] = useState('')
  const [pending,startTransition] = useTransition()
  return <div className="flex flex-col items-start gap-2">
    <button className="btn" disabled={pending} onClick={()=>{
      setMsg(''); setErr('')
      startTransition(async()=>{
        try{
          const r = await pollJob<any>(api, '/api/discovery/recover-serp-rejects', {limit:4}, {maxWait:180000, interval:3000})
          setMsg(`Recovered cards=${r.cards}, rewrites=${r.created_rewrites?.length||0}, rejected=${r.rejected?.length||0}`)
          router.refresh()
        }catch(e:any){ setErr(e.message || 'Recovery failed') }
      })
    }}>{pending?'Recovering...':'Recover SERP rejects'}</button>
    {msg&&<span className="text-xs text-emerald-300">{msg}</span>}
    {err&&<span className="text-xs text-rose-300">{err}</span>}
  </div>
}
