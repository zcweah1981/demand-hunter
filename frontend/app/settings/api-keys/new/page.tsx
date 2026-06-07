'use client'
import {useEffect, useState} from 'react'
import Link from 'next/link'
import {useSearchParams, useRouter} from 'next/navigation'
import {api} from '../../../../lib/api'

function SecretInput({value,onChange,placeholder=''}:{value:string;onChange:(v:string)=>void;placeholder?:string}){
 const [show,setShow]=useState(false)
 return <div className="flex gap-2"><input className="input flex-1 font-mono text-sm" type={show?'text':'password'} value={value} placeholder={placeholder} onChange={e=>onChange(e.target.value)}/><button type="button" className="btn-secondary" onClick={()=>setShow(!show)}>{show?'隐藏':'显示'}</button></div>
}

export default function Page(){
 const params=useSearchParams(); const router=useRouter()
 const typeId=params.get('type')||'serpapi'
 const [data,setData]=useState<any>(null)
 const [values,setValues]=useState<Record<string,string>>({})
 const [busy,setBusy]=useState(false)
 const [msg,setMsg]=useState('')
 useEffect(()=>{api<any>(`/api/settings/api-key-types/${typeId}`).then(r=>{setData(r.type); const v:any={}; (r.type?.fields||[]).forEach((f:any)=>v[f.name]=''); setValues(v)}).catch(e=>setMsg(`❌ ${e.message}`))},[typeId])
 async function save(){
  setBusy(true); setMsg('')
  try{
   const r=await api<any>('/api/settings/api-keys',{method:'POST',body:JSON.stringify({type_id:typeId,values})})
   if(r.ok===false) throw new Error(r.error||'保存失败')
   setMsg('✅ 已保存')
   setTimeout(()=>router.push('/settings/api-keys'),300)
  }catch(e:any){setMsg(`❌ ${e.message}`)} finally{setBusy(false)}
 }
 if(!data) return <div className="panel">加载中... {msg}</div>
 return <div className="mx-auto max-w-3xl space-y-6">
  <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-6 shadow-2xl">
   <Link href="/settings/api-keys" className="text-sm text-blue-300 no-underline">← 返回 API Key 管理中心</Link>
   <h1 className="mt-4 text-3xl font-black">新增 {data.title}</h1>
   <p className="mt-2 text-sm text-slate-400">类型固定：{data.category} · {data.free_quota||'—'}</p>
   <div className="mt-3 font-mono text-xs text-slate-600">{data.setting_key}</div>
  </section>
  <section className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6 shadow-xl shadow-black/10">
   <div className="space-y-4">
    {(data.fields||[]).map((f:any)=><label key={f.name} className="block"><span className="mb-1 block text-sm font-bold text-slate-300">{f.label}</span>{f.secret?<SecretInput value={values[f.name]||''} placeholder={f.kind==='password'?'secret...':'key/token...'} onChange={v=>setValues({...values,[f.name]:v})}/>:<input className="input w-full font-mono text-sm" value={values[f.name]||''} placeholder={f.name} onChange={e=>setValues({...values,[f.name]:e.target.value})}/>}</label>)}
   </div>
   <div className="mt-6 flex flex-wrap gap-2"><button className="btn" disabled={busy} onClick={save}>{busy?'保存中...':'保存'}</button><Link className="btn-secondary no-underline" href="/settings/api-keys">取消</Link></div>
   {msg&&<div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-300">{msg}</div>}
  </section>
 </div>
}
