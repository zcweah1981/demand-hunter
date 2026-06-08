'use client'
import Link from 'next/link'
import {useState} from 'react'
import {api} from '../lib/api'

export function ApiKeyActions({typeId,index}:{typeId:string;index:number}){
 const [busy,setBusy]=useState(false)
 async function remove(){
  if(!confirm(`删除 ${typeId} #${index}？\n\n删除后不可直接恢复，请确认。`)) return
  setBusy(true)
  try{
   const r=await api<any>('/api/settings/api-keys/remove',{method:'POST',body:JSON.stringify({type_id:typeId,index})})
   if(r.ok===false) throw new Error(r.error||'删除失败')
   location.reload()
  }catch(e:any){alert(e.message); setBusy(false)}
 }
 return <div className="flex gap-1"><Link className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-200 no-underline hover:bg-slate-700" href={`/settings/api-keys/new?type=${typeId}&index=${index}`}>修改</Link><button className="rounded bg-rose-950/60 px-2 py-1 text-xs text-rose-200 hover:bg-rose-900 disabled:opacity-50" disabled={busy} onClick={remove}>{busy?'删除中':'删除'}</button></div>
}
