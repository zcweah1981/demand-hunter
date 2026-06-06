'use client'
import {useMemo, useState} from 'react'
import Link from 'next/link'
import {api} from '../lib/api'
import {useLang} from '../lib/i18n'

const GROUPS:any[]=[
 {id:'search',titleKey:'searchProviders',descKey:'searchDesc',keys:['SERP_PROVIDER_ORDER','SERP_PROVIDER_ATTEMPT_LIMIT','SEARXNG_URLS','SEARXNG_URL','SEARXNG_ROTATION_STRATEGY','SEARXNG_ENGINES','SEARXNG_API_TOKEN','FOUR_FIND_SERP_STRATEGY_ENABLED','FOUR_FIND_SERP_VARIANT_LIMIT']},
 {id:'brave',title:'Brave',descKey:'braveDesc',keys:['BRAVE_API_KEYS']},
 {id:'tavily',title:'Tavily',descKey:'tavilyDesc',keys:['TAVILY_API_KEYS']},
 {id:'llm',title:'LLM',descKey:'llmDesc',keys:['LLM_PRIMARY_PROVIDER','LLM_PRIMARY_MODEL','LLM_PRIMARY_API_KEY','LLM_FALLBACKS']},
 {id:'automation',titleKey:'automation',descKey:'automationDesc',keys:['AUTO_RUN_ENABLED','AUTO_RUN_INTERVAL_MINUTES','AUTO_RUN_LIMIT','FOUR_FIND_AUTO_ENABLED','FOUR_FIND_AUTO_SEEDS','FOUR_FIND_IMPORT_LIMIT','FOUR_FIND_REWRITE_ON_SERP_REJECT','FOUR_FIND_REWRITE_LIMIT']},
 {id:'quality',titleKey:'quality',descKey:'qualityDesc',keys:['MIN_ACTION_SCORE','REQUIRE_SOCIAL_FOR_ACTION','COLLECT_SOCIAL_EVIDENCE','BLOCKED_TERMS']},
 {id:'security',titleKey:'security',descKey:'securityDesc',keys:[]},
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
 const {t}=useLang()
 const [items,setItems]=useState<Setting[]>(rows)
 const [active,setActive]=useState(initialGroup)
 const [msg,setMsg]=useState('')
 const [testing,setTesting]=useState(false)
 const [currentPassword,setCurrentPassword]=useState('')
 const [newPassword,setNewPassword]=useState('')
 const [pendingAdd,setPendingAdd]=useState<Record<string,string>>({})
 const byKey=useMemo(()=>Object.fromEntries(items.map((x:any)=>[x.key,x])),[items])
 const group=GROUPS.find(g=>g.id===active)||GROUPS[0]
 function settingFor(key:string):Setting{return byKey[key]||{key,value:'',secret:SECRET_KEYS.includes(key)}}
 function update(key:string, patch:Partial<Setting>){setItems(items.map((x:any)=>x.key===key?{...x,...patch}:x).concat(byKey[key]?[]:[{key,value:'',secret:SECRET_KEYS.includes(key),...patch} as Setting]))}
 async function saveGroup(keys:string[]){for(const k of keys){const s=settingFor(k); if(s.secret&&masked(s.value)) continue; await api('/api/settings',{method:'POST',body:JSON.stringify(s)})} setMsg(`${t('saved')} ${group.title||t(group.titleKey)}`)}
 async function test(){setTesting(true);setMsg(t('testing')); try{const r=await api<any>('/api/settings/test-search',{method:'POST'}); const p=r.providers||{}; setMsg(r.ok?`✅ ${t('searchOk')}: ${r.result_count} results, ${r.elapsed_ms}ms · providers=${(p.available||[]).join(',')||'none'} · searxng=${p.searxng_urls||0} · braveKeys=${p.brave_keys||0} · tavilyKeys=${p.tavily_keys||0}`:`❌ ${t('searchFailed')}: ${r.error}`)}catch(e:any){setMsg(`❌ ${e.message}`)} finally{setTesting(false)}}
 async function changePassword(){setMsg(t('changingPassword')); try{await api('/api/auth/password',{method:'POST',body:JSON.stringify({current_password:currentPassword,new_password:newPassword})}); setCurrentPassword(''); setNewPassword(''); setMsg(`✅ ${t('passwordChanged')}`)}catch(e:any){setMsg(`❌ ${e.message}`)}}
 function setListItem(key:string, idx:number, value:string){const xs=splitList(settingFor(key).value); xs[idx]=value; update(key,{value:joinList(xs)})}
 function addListItem(key:string){const cur=settingFor(key).value||''; update(key,{value:cur+(cur.trim()?'\n':'')})}
 function removeListItem(key:string, idx:number){const xs=splitList(settingFor(key).value); xs.splice(idx,1); update(key,{value:joinList(xs)})}
 return <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
  <aside className="panel h-fit space-y-2 lg:sticky lg:top-6">
   <div className="mb-3 px-2 text-xs font-bold uppercase tracking-[0.25em] text-slate-500">{t('settingsMenu')}</div>
   {GROUPS.map(g=><Link href={`/settings/${g.id}`} key={g.id} onClick={()=>setActive(g.id)} className={`w-full rounded-2xl px-4 py-3 text-left transition ${active===g.id?'bg-blue-600/20 text-blue-100 ring-1 ring-blue-500/50':'bg-slate-950/50 text-slate-300 hover:bg-slate-900'}`}><div className="font-bold">{g.title||t(g.titleKey)}</div><div className="mt-1 text-xs text-slate-500">{g.desc||t(g.descKey)}</div></Link>)}
  </aside>
  <main className="space-y-5">
   <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-6 shadow-2xl">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><div className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">{t('configuration')}</div><h2 className="mt-2 text-3xl font-black">{group.title||t(group.titleKey)}</h2><p className="mt-1 text-sm text-slate-400">{group.desc||t(group.descKey)}</p></div><div className="flex gap-2">{active==='search'&&<button className="btn-secondary" disabled={testing} onClick={test}>{testing?t('testing'):t('testProviders')}</button>}{group.keys.length>0&&<button className="btn" onClick={()=>saveGroup(group.keys)}>{t('saveGroup')}</button>}</div></div>
    {msg&&<div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-200">{msg}</div>}
   </section>
   {active==='security'?<section className="panel space-y-4"><h3 className="text-xl font-bold">{t('changePassword')}</h3><div className="grid gap-3 md:grid-cols-2"><input className="input" type="password" placeholder={t('currentPassword')} value={currentPassword} onChange={e=>setCurrentPassword(e.target.value)}/><input className="input" type="password" placeholder={t('newPassword')} value={newPassword} onChange={e=>setNewPassword(e.target.value)}/></div><button className="btn" disabled={!newPassword||newPassword.length<8} onClick={changePassword}>{t('updatePassword')}</button></section>:<section className="space-y-4">{group.keys.map((key:string)=>renderSetting(key))}</section>}
  </main>
 </div>

 function renderSetting(key:string){const s=settingFor(key); const bool=BOOL_KEYS.includes(key); const list=LIST_KEYS.includes(key); const multi=MULTILINE_KEYS.includes(key); const values=splitList(s.value); const fallback=key==='LLM_FALLBACKS'; return <div key={key} className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl shadow-black/10"><div className="mb-4 flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><h3 className="font-bold text-slate-100">{key}</h3>{s.secret&&<span className="badge">{t('secret')}</span>}{list&&<span className="badge badge-action">{t('rotation')}</span>}</div><div className="mt-1 text-xs text-slate-500">{s.updated_at?new Date(s.updated_at).toLocaleString():t('notSaved')}</div>{list&&<p className="mt-2 text-xs text-blue-300">{t('rotationHint')}</p>}{fallback&&<p className="mt-2 text-xs text-blue-300">{t('fallbackHint')}</p>}</div><div className="flex gap-2"><label className="flex items-center gap-2 text-xs text-slate-400"><input type="checkbox" checked={!!s.secret} onChange={e=>update(key,{secret:e.target.checked})}/> {t('secret')}</label></div></div>{bool?<select className="input w-full" value={s.value||'false'} onChange={e=>update(key,{value:e.target.value})}><option value="true">true</option><option value="false">false</option></select>:list?<div className="space-y-3"><div className="space-y-2">{values.length?values.map((v,i)=><div key={i} className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/60 p-3"><div className="flex-1 font-mono text-sm text-slate-200">{masked(v)?v:v}</div><button className="btn-secondary" onClick={()=>removeListItem(key,i)}>{t('remove')}</button></div>):<div className="rounded-2xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">{t('noEntries')}</div>}</div><div className="flex gap-2"><input className="input flex-1 font-mono text-sm" type={s.secret?'password':'text'} value={pendingAdd[key]||''} placeholder={key==='SEARXNG_URLS'?'http://searxng:8080':t('pasteNewApiKey')} onChange={e=>setPendingAdd({...pendingAdd,[key]:e.target.value})}/><button className="btn" disabled={!(pendingAdd[key]||'').trim()} onClick={()=>{const xs=splitList(s.value); xs.push((pendingAdd[key]||'').trim()); update(key,{value:joinList(xs)}); setPendingAdd({...pendingAdd,[key]:''})}}>{t('confirmAdd')}</button></div><textarea className="input min-h-24 w-full font-mono text-xs" value={s.value||''} onChange={e=>update(key,{value:e.target.value})} placeholder={t('pasteBulk')}/></div>:fallback?<textarea className="input min-h-44 w-full font-mono text-sm" value={s.value||''} onChange={e=>update(key,{value:e.target.value})} placeholder={'[{"provider":"openai","model":"gpt-4o-mini","api_key":"..."}]'}/>:multi?<textarea className="input min-h-28 w-full font-mono text-sm" value={s.value||''} onChange={e=>update(key,{value:e.target.value})}/>:<input className="input w-full" type={s.secret?'password':'text'} value={masked(s.value)?'':s.value||''} placeholder={masked(s.value)?s.value:''} onChange={e=>update(key,{value:e.target.value})}/>}</div>}
}
