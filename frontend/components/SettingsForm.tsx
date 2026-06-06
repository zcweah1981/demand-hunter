'use client'
import {useMemo, useState} from 'react'
import Link from 'next/link'
import {api} from '../lib/api'

const GROUPS:any[]=[
 {id:'search',title:'Search Providers',desc:'SearXNG 多地址、provider fallback、SERP strategy',keys:['SERP_PROVIDER_ORDER','SERP_PROVIDER_ATTEMPT_LIMIT','SEARXNG_URLS','SEARXNG_URL','SEARXNG_ROTATION_STRATEGY','SEARXNG_ENGINES','SEARXNG_API_TOKEN','FOUR_FIND_SERP_STRATEGY_ENABLED','FOUR_FIND_SERP_VARIANT_LIMIT']},
 {id:'brave',title:'Brave',desc:'Brave 多 Key 轮询',keys:['BRAVE_API_KEYS','BRAVE_API_KEY']},
 {id:'tavily',title:'Tavily',desc:'Tavily 多 Key 轮询',keys:['TAVILY_API_KEYS','TAVILY_API_KEY']},
 {id:'llm',title:'LLM',desc:'Primary + fallback 模型配置',keys:['LLM_PRIMARY_PROVIDER','LLM_PRIMARY_MODEL','LLM_PRIMARY_API_KEY','LLM_FALLBACKS','LLM_PROVIDER','LLM_API_KEY']},
 {id:'automation',title:'Automation',desc:'自动运行和 Four-Find 闭环策略',keys:['AUTO_RUN_ENABLED','AUTO_RUN_INTERVAL_MINUTES','AUTO_RUN_LIMIT','FOUR_FIND_AUTO_ENABLED','FOUR_FIND_AUTO_SEEDS','FOUR_FIND_IMPORT_LIMIT','FOUR_FIND_REWRITE_ON_SERP_REJECT','FOUR_FIND_REWRITE_LIMIT']},
 {id:'quality',title:'Quality',desc:'Action 门槛和噪音控制',keys:['MIN_ACTION_SCORE','REQUIRE_SOCIAL_FOR_ACTION','COLLECT_SOCIAL_EVIDENCE','BLOCKED_TERMS']},
 {id:'security',title:'Security',desc:'登录密码修改',keys:[]},
]
const BOOL_KEYS=['AUTO_RUN_ENABLED','REQUIRE_SOCIAL_FOR_ACTION','COLLECT_SOCIAL_EVIDENCE','FOUR_FIND_AUTO_ENABLED','FOUR_FIND_SERP_STRATEGY_ENABLED','FOUR_FIND_REWRITE_ON_SERP_REJECT']
const SECRET_KEYS=['SEARXNG_API_TOKEN','BRAVE_API_KEY','BRAVE_API_KEYS','TAVILY_API_KEY','TAVILY_API_KEYS','LLM_API_KEY','LLM_PRIMARY_API_KEY','LLM_FALLBACKS']
const LIST_KEYS=['SEARXNG_URLS','BRAVE_API_KEYS','TAVILY_API_KEYS']
const MULTILINE_KEYS=['FOUR_FIND_AUTO_SEEDS','BLOCKED_TERMS']

type Setting={key:string;value:string;secret:boolean;updated_at?:string}
function splitList(v:string){return (v||'').split(/[\n,]+/).map(x=>x.trim()).filter(Boolean)}
function joinList(xs:string[]){return xs.map(x=>x.trim()).filter(Boolean).join('\n')}
function masked(v:string){return v&&v.startsWith('***')}

export function SettingsForm({rows, initialGroup='search'}:{rows:any[]; initialGroup?:string}){
 const [items,setItems]=useState<Setting[]>(rows)
 const [active,setActive]=useState(initialGroup)
 const [msg,setMsg]=useState('')
 const [testing,setTesting]=useState(false)
 const [currentPassword,setCurrentPassword]=useState('')
 const [newPassword,setNewPassword]=useState('')
 const byKey=useMemo(()=>Object.fromEntries(items.map((x:any)=>[x.key,x])),[items])
 const group=GROUPS.find(g=>g.id===active)||GROUPS[0]
 function settingFor(key:string):Setting{return byKey[key]||{key,value:'',secret:SECRET_KEYS.includes(key)}}
 function update(key:string, patch:Partial<Setting>){setItems(items.map((x:any)=>x.key===key?{...x,...patch}:x).concat(byKey[key]?[]:[{key,value:'',secret:SECRET_KEYS.includes(key),...patch} as Setting]))}
 async function save(key:string){const s=settingFor(key); await api('/api/settings',{method:'POST',body:JSON.stringify(s)}); setMsg(`Saved ${key}`)}
 async function saveGroup(keys:string[]){for(const k of keys){await api('/api/settings',{method:'POST',body:JSON.stringify(settingFor(k))})} setMsg(`Saved ${group.title}`)}
 async function test(){setTesting(true);setMsg('Testing search providers...'); try{const r=await api<any>('/api/settings/test-search',{method:'POST'}); const p=r.providers||{}; setMsg(r.ok?`✅ Search OK: ${r.result_count} results, ${r.elapsed_ms}ms · providers=${(p.available||[]).join(',')||'none'} · searxng=${p.searxng_urls||0} · braveKeys=${p.brave_keys||0} · tavilyKeys=${p.tavily_keys||0}`:`❌ Search failed: ${r.error}`)}catch(e:any){setMsg(`❌ ${e.message}`)} finally{setTesting(false)}}
 async function changePassword(){setMsg('Changing password...'); try{await api('/api/auth/password',{method:'POST',body:JSON.stringify({current_password:currentPassword,new_password:newPassword})}); setCurrentPassword(''); setNewPassword(''); setMsg('✅ Password changed')}catch(e:any){setMsg(`❌ ${e.message}`)}}
 function setListItem(key:string, idx:number, value:string){const xs=splitList(settingFor(key).value); xs[idx]=value; update(key,{value:joinList(xs)})}
 function addListItem(key:string){const cur=settingFor(key).value||''; update(key,{value:cur+(cur.trim()?'\n':'')})}
 function removeListItem(key:string, idx:number){const xs=splitList(settingFor(key).value); xs.splice(idx,1); update(key,{value:joinList(xs)})}
 return <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
  <aside className="panel h-fit space-y-2 lg:sticky lg:top-6">
   <div className="mb-3 px-2 text-xs font-bold uppercase tracking-[0.25em] text-slate-500">Settings</div>
   {GROUPS.map(g=><Link href={`/settings/${g.id}`} key={g.id} onClick={()=>setActive(g.id)} className={`w-full rounded-2xl px-4 py-3 text-left transition ${active===g.id?'bg-blue-600/20 text-blue-100 ring-1 ring-blue-500/50':'bg-slate-950/50 text-slate-300 hover:bg-slate-900'}`}><div className="font-bold">{g.title}</div><div className="mt-1 text-xs text-slate-500">{g.desc}</div></Link>)}
  </aside>
  <main className="space-y-5">
   <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-6 shadow-2xl">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><div className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">Configuration</div><h2 className="mt-2 text-3xl font-black">{group.title}</h2><p className="mt-1 text-sm text-slate-400">{group.desc}</p></div><div className="flex gap-2">{active==='search'&&<button className="btn-secondary" disabled={testing} onClick={test}>{testing?'Testing...':'Test Providers'}</button>}{group.keys.length>0&&<button className="btn" onClick={()=>saveGroup(group.keys)}>Save group</button>}</div></div>
    {msg&&<div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-200">{msg}</div>}
   </section>
   {active==='security'?<section className="panel space-y-4"><h3 className="text-xl font-bold">Change login password</h3><div className="grid gap-3 md:grid-cols-2"><input className="input" type="password" placeholder="Current password" value={currentPassword} onChange={e=>setCurrentPassword(e.target.value)}/><input className="input" type="password" placeholder="New password (min 8 chars)" value={newPassword} onChange={e=>setNewPassword(e.target.value)}/></div><button className="btn" disabled={!newPassword||newPassword.length<8} onClick={changePassword}>Update password</button></section>:<section className="space-y-4">{group.keys.map((key:string)=>renderSetting(key))}</section>}
  </main>
 </div>

 function renderSetting(key:string){const s=settingFor(key); const bool=BOOL_KEYS.includes(key); const list=LIST_KEYS.includes(key); const multi=MULTILINE_KEYS.includes(key); const values=splitList(s.value); const fallback=key==='LLM_FALLBACKS'; return <div key={key} className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl shadow-black/10"><div className="mb-4 flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><h3 className="font-bold text-slate-100">{key}</h3>{s.secret&&<span className="badge">secret</span>}{list&&<span className="badge badge-action">rotation</span>}</div><div className="mt-1 text-xs text-slate-500">{s.updated_at?new Date(s.updated_at).toLocaleString():'not saved yet'}</div>{list&&<p className="mt-2 text-xs text-blue-300">支持多条，按顺序轮询；某条失败自动尝试下一条。</p>}{fallback&&<p className="mt-2 text-xs text-blue-300">JSON 数组：provider/model/api_key。Primary 失败后按顺序 fallback。</p>}</div><div className="flex gap-2"><label className="flex items-center gap-2 text-xs text-slate-400"><input type="checkbox" checked={!!s.secret} onChange={e=>update(key,{secret:e.target.checked})}/> secret</label><button className="btn" onClick={()=>save(key)}>Save</button></div></div>{bool?<select className="input w-full" value={s.value||'false'} onChange={e=>update(key,{value:e.target.value})}><option value="true">true</option><option value="false">false</option></select>:list?<div className="space-y-3"><div className="space-y-2">{(values.length?values:['']).map((v,i)=><div key={i} className="flex gap-2"><input className="input flex-1 font-mono text-sm" type={s.secret?'password':'text'} value={masked(v)?'':v} placeholder={masked(v)?v:(key==='SEARXNG_URLS'?'http://searxng:8080':'API key')} onChange={e=>setListItem(key,i,e.target.value)}/><button className="btn-secondary" onClick={()=>removeListItem(key,i)}>Remove</button></div>)}</div><button className="btn-secondary" onClick={()=>addListItem(key)}>+ Add</button><textarea className="input min-h-24 w-full font-mono text-xs" value={s.value||''} onChange={e=>update(key,{value:e.target.value})} placeholder="也可直接批量粘贴，每行一条"/></div>:fallback?<textarea className="input min-h-44 w-full font-mono text-sm" value={s.value||''} onChange={e=>update(key,{value:e.target.value})} placeholder={'[{"provider":"openai","model":"gpt-4o-mini","api_key":"..."}]'}/>:multi?<textarea className="input min-h-28 w-full font-mono text-sm" value={s.value||''} onChange={e=>update(key,{value:e.target.value})}/>:<input className="input w-full" type={s.secret?'password':'text'} value={masked(s.value)?'':s.value||''} placeholder={masked(s.value)?s.value:''} onChange={e=>update(key,{value:e.target.value})}/>}</div>}
}
