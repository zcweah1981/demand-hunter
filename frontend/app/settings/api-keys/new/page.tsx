'use client'
import {useEffect, useMemo, useState} from 'react'
import Link from 'next/link'
import {useSearchParams, useRouter} from 'next/navigation'
import {api} from '../../../../lib/api'

function SecretInput({value,onChange,placeholder=''}:{value:string;onChange:(v:string)=>void;placeholder?:string}){
 const [show,setShow]=useState(false)
 return <div className="flex gap-2"><input className="input flex-1 font-mono text-sm" type={show?'text':'password'} value={value} placeholder={placeholder} onChange={e=>onChange(e.target.value)}/><button type="button" className="btn-secondary" onClick={()=>setShow(!show)}>{show?'隐藏':'显示'}</button></div>
}

export default function Page(){
 const params=useSearchParams(); const router=useRouter()
 const initial=params.get('type')||''
 const [types,setTypes]=useState<any[]>([])
 const [typeId,setTypeId]=useState(initial)
 const [values,setValues]=useState<Record<string,string>>({})
 const [busy,setBusy]=useState(false)
 const [msg,setMsg]=useState('')
 useEffect(()=>{api<any>('/api/settings/api-key-types').then(r=>{setTypes(r.types||[]); const chosen=initial||((r.types||[])[0]?.id||''); setTypeId(chosen)}).catch(e=>setMsg(`❌ ${e.message}`))},[])
 const data=useMemo(()=>types.find(t=>t.id===typeId),[types,typeId])
 useEffect(()=>{if(!data) return; const v:any={}; (data.fields||[]).forEach((f:any)=>v[f.name]=''); setValues(v)},[data?.id])
 async function save(){
  setBusy(true); setMsg('')
  try{
   const r=await api<any>('/api/settings/api-keys',{method:'POST',body:JSON.stringify({type_id:typeId,values})})
   if(r.ok===false) throw new Error(r.error||'保存失败')
   setMsg('✅ 已保存')
   setTimeout(()=>router.push('/settings/api-keys'),300)
  }catch(e:any){setMsg(`❌ ${e.message}`)} finally{setBusy(false)}
 }
 if(!types.length) return <div className="panel">加载中... {msg}</div>
 return <div className="mx-auto max-w-3xl space-y-6">
  <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-6 shadow-2xl">
   <Link href="/settings/api-keys" className="text-sm text-blue-300 no-underline">← 返回 API Key 管理中心</Link>
   <h1 className="mt-4 text-3xl font-black">新增 Key</h1>
   <p className="mt-2 text-sm text-slate-400">先选择固定 Key 类型；如果是组合型凭证，会在同一页一次填完。</p>
  </section>
  <section className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6 shadow-xl shadow-black/10">
   <label className="block"><span className="mb-1 block text-sm font-bold text-slate-300">Key 类型</span><select className="input w-full" value={typeId} onChange={e=>setTypeId(e.target.value)}>{types.map((t:any)=><option key={t.id} value={t.id}>{t.title} · {t.category}</option>)}</select></label>
   {data&&<div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/50 p-4 text-sm text-slate-400"><div className="font-bold text-slate-100">{data.title}</div><div className="mt-1">{data.category} · {data.free_quota||'—'}</div><div className="mt-1 font-mono text-xs text-slate-600">{data.setting_key}</div></div>}
   <div className="mt-5 space-y-4">
    {(data?.fields||[]).map((f:any)=><label key={f.name} className="block"><span className="mb-1 block text-sm font-bold text-slate-300">{f.label}</span>{f.secret?<SecretInput value={values[f.name]||''} placeholder={f.kind==='password'?'secret...':'key/token...'} onChange={v=>setValues({...values,[f.name]:v})}/>:<input className="input w-full font-mono text-sm" value={values[f.name]||''} placeholder={f.name} onChange={e=>setValues({...values,[f.name]:e.target.value})}/>}</label>)}
   </div>
   <div className="mt-6 flex flex-wrap gap-2"><button className="btn" disabled={busy||!typeId} onClick={save}>{busy?'保存中...':'保存'}</button><Link className="btn-secondary no-underline" href="/settings/api-keys">取消</Link></div>
   {msg&&<div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-300">{msg}</div>}
  </section>
 </div>
}
