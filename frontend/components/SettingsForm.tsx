'use client'
import {useState} from 'react'
import {api} from '../lib/api'
export function SettingsForm({rows}:{rows:any[]}){
 const [items,setItems]=useState(rows); const [msg,setMsg]=useState('')
 async function save(s:any){await api('/api/settings',{method:'POST',body:JSON.stringify(s)}); setMsg(`Saved ${s.key}`)}
 async function test(){setMsg('Testing SearXNG...'); const r=await api<any>('/api/settings/test-search',{method:'POST'}); setMsg(r.ok?`SearXNG OK: ${r.result_count} results, ${r.elapsed_ms}ms`:`SearXNG failed: ${r.error}`)}
 return <div className="space-y-4"><div className="flex gap-2"><button className="btn" onClick={test}>Test SearXNG</button>{msg&&<span className="text-sm text-green-300">{msg}</span>}</div><div className="card space-y-3">{items.map((s,i)=><div key={s.key} className="grid grid-cols-12 gap-3 border-t border-slate-800 py-3"><label className="col-span-3 font-semibold">{s.key}</label><input className="input col-span-6" value={s.value||''} onChange={e=>{const n=[...items]; n[i]={...s,value:e.target.value}; setItems(n)}}/><label className="col-span-1 flex items-center gap-1 text-xs"><input type="checkbox" checked={!!s.secret} onChange={e=>{const n=[...items]; n[i]={...s,secret:e.target.checked}; setItems(n)}}/> secret</label><button className="btn col-span-2" onClick={()=>save(items[i])}>Save</button></div>)}</div></div>
}
