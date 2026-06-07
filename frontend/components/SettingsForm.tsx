'use client'
import {useEffect, useMemo, useState} from 'react'
import Link from 'next/link'
import {api} from '../lib/api'
import {useLang} from '../lib/i18n'
import {ProviderHealthPanel} from './ProviderHealthPanel'

const GROUPS:any[]=[
 {id:'search',titleKey:'searchProviders',descKey:'searchDesc',keys:['SERP_PROVIDER_ORDER','SERP_PROVIDER_ATTEMPT_LIMIT','FOUR_FIND_SERP_STRATEGY_ENABLED','FOUR_FIND_SERP_VARIANT_LIMIT']},
 {id:'searxng',title:'SearXNG',descKey:'searxngDesc',keys:['SEARXNG_ENDPOINTS']},
 {id:'brave',title:'Brave',descKey:'braveDesc',keys:['BRAVE_API_KEYS']},
 {id:'tavily',title:'Tavily',descKey:'tavilyDesc',keys:['TAVILY_API_KEYS']},
 {id:'llm',title:'LLM',descKey:'llmDesc',keys:['LLM_PRIMARY_BASE_URL','LLM_PRIMARY_API_KEY','LLM_PRIMARY_MODEL','LLM_FALLBACKS']},
 {id:'automation',titleKey:'automation',descKey:'automationDesc',keys:['AUTO_RUN_ENABLED','AUTO_RUN_INTERVAL_MINUTES','AUTO_RUN_LIMIT','FOUR_FIND_AUTO_ENABLED','FOUR_FIND_AUTO_SEEDS','FOUR_FIND_AUTO_DOMAINS','FOUR_FIND_IMPORT_LIMIT','FOUR_FIND_REWRITE_ON_SERP_REJECT','FOUR_FIND_REWRITE_LIMIT']},
 {id:'quality',titleKey:'quality',descKey:'qualityDesc',keys:['MIN_ACTION_SCORE','REQUIRE_SOCIAL_FOR_ACTION','COLLECT_SOCIAL_EVIDENCE','BLOCKED_TERMS']},
 {id:'security',titleKey:'security',descKey:'securityDesc',keys:[]},
]
const BOOL_KEYS=['AUTO_RUN_ENABLED','REQUIRE_SOCIAL_FOR_ACTION','COLLECT_SOCIAL_EVIDENCE','FOUR_FIND_AUTO_ENABLED','FOUR_FIND_SERP_STRATEGY_ENABLED','FOUR_FIND_REWRITE_ON_SERP_REJECT']
const SECRET_KEYS=['SEARXNG_API_TOKEN','BRAVE_API_KEY','BRAVE_API_KEYS','TAVILY_API_KEY','TAVILY_API_KEYS','LLM_API_KEY','LLM_PRIMARY_API_KEY','LLM_FALLBACKS']
const LIST_KEYS=['BRAVE_API_KEYS','TAVILY_API_KEYS']
const MULTILINE_KEYS=['FOUR_FIND_AUTO_SEEDS','FOUR_FIND_AUTO_DOMAINS','BLOCKED_TERMS']

const KEY_LABELS:Record<string,string>={
 SERP_PROVIDER_ORDER:'搜索源顺序', SERP_PROVIDER_ATTEMPT_LIMIT:'搜索源尝试次数', FOUR_FIND_SERP_STRATEGY_ENABLED:'启用 SERP 自动策略', FOUR_FIND_SERP_VARIANT_LIMIT:'SERP 查询变体数量',
 SEARXNG_ENDPOINTS:'SearXNG 实例', SEARXNG_ROTATION_STRATEGY:'轮询策略', SEARXNG_ENGINES:'默认搜索引擎（旧配置）',
 BRAVE_API_KEYS:'Brave 密钥列表', TAVILY_API_KEYS:'Tavily 密钥列表',
 LLM_PRIMARY_BASE_URL:'Base URL', LLM_PRIMARY_PROVIDER:'主模型提供商', LLM_PRIMARY_MODEL:'主模型', LLM_PRIMARY_API_KEY:'主模型密钥', LLM_FALLBACKS:'备用模型',
 AUTO_RUN_ENABLED:'启用自动运行', AUTO_RUN_INTERVAL_MINUTES:'自动运行间隔（分钟）', AUTO_RUN_LIMIT:'每轮处理数量', FOUR_FIND_AUTO_ENABLED:'启用四找闭环', FOUR_FIND_AUTO_SEEDS:'自动种子词', FOUR_FIND_AUTO_DOMAINS:'自动竞品域名', FOUR_FIND_IMPORT_LIMIT:'四找导入数量', FOUR_FIND_REWRITE_ON_SERP_REJECT:'SERP 失败后自动改写', FOUR_FIND_REWRITE_LIMIT:'改写恢复数量',
 MIN_ACTION_SCORE:'Action 最低分', REQUIRE_SOCIAL_FOR_ACTION:'Action 必须有社媒证据', COLLECT_SOCIAL_EVIDENCE:'采集社媒证据', BLOCKED_TERMS:'屏蔽词',
}

type Setting={key:string;value:string;secret:boolean;updated_at?:string}
function splitList(v:string){return (v||'').split(/[\n,]+/).map(x=>x.trim()).filter(Boolean)}
function joinList(xs:string[]){return xs.map(x=>x.trim()).filter(Boolean).join('\n')}
function masked(v:string){return v&&v.startsWith('***')}

function SearxngEndpointManager(){
 const {t}=useLang()
 const [rows,setRows]=useState<any[]>([])
 const [busy,setBusy]=useState(false)
 const [msg,setMsg]=useState('')
 async function load(){const r=await api<any>('/api/settings/searxng/endpoints'); setRows(r.items||[])}
 useEffect(()=>{load().catch(()=>{})},[])
 function add(){setRows([...rows,{url:'',api_token:'',has_token:false,use_builtin_engines:true,engines:''}])}
 function update(i:number,patch:any){setRows(rows.map((r,idx)=>idx===i?{...r,...patch}:r))}
 function remove(i:number){setRows(rows.filter((_,idx)=>idx!==i))}
 async function save(){
  setBusy(true); setMsg('')
  try{
   const endpoints=rows.map(r=>({url:(r.url||'').trim(),api_token:(r.api_token||'').trim(),use_builtin_engines:r.use_builtin_engines!==false,engines:(r.engines||'').trim()})).filter(r=>r.url)
   const saved=await api<any>('/api/settings/searxng/endpoints',{method:'POST',body:JSON.stringify({endpoints})})
   setRows(saved.items||[]); setMsg(`✅ ${t('saved')}`)
  }catch(e:any){setMsg(`❌ ${e.message}`)} finally{setBusy(false)}
 }
 return <div className="space-y-3">
  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
   <div className="mb-3 flex flex-wrap items-center justify-between gap-3"><div><b>{rows.length} 个 SearXNG 实例</b><p className="text-xs text-slate-500">每一条都可以单独设置 URL、X-API-TOKEN、是否采用内置搜索引擎。</p></div><button className="btn" disabled={busy} onClick={save}>{busy?t('saving'):'保存 SearXNG'}</button></div>
   <div className="space-y-3">{rows.length?rows.map((row,i)=><div key={i} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
    <div className="mb-3 flex items-center justify-between gap-3"><span className="text-sm text-slate-500">#{i+1}</span><button className="btn-secondary" onClick={()=>remove(i)}>{t('remove')}</button></div>
    <div className="grid gap-3 lg:grid-cols-2">
     <label className="block"><span className="mb-1 block text-xs text-slate-500">地址 URL</span><input className="input font-mono text-sm" value={row.url||''} placeholder="http://searxng:8080" onChange={e=>update(i,{url:e.target.value})}/></label>
     <label className="block"><span className="mb-1 block text-xs text-slate-500">访问令牌 X-API-TOKEN</span><input className="input font-mono text-sm" type="password" value={row.api_token?.startsWith('***')?'':(row.api_token||'')} placeholder={row.api_token?.startsWith('***')?row.api_token:'可不填'} onChange={e=>update(i,{api_token:e.target.value})}/></label>
    </div>
    <div className="mt-3 rounded-xl border border-slate-800 bg-slate-900/60 p-3">
     <label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={row.use_builtin_engines!==false} onChange={e=>update(i,{use_builtin_engines:e.target.checked})}/> 搜索引擎采用内置</label>
     <p className="mt-1 text-xs text-slate-500">开启时不传 engines 参数，使用该 SearXNG 实例自己的默认搜索引擎。</p>
     {row.use_builtin_engines===false&&<label className="mt-3 block"><span className="mb-1 block text-xs text-slate-500">自定义搜索引擎 engines</span><input className="input font-mono text-sm" value={row.engines||''} placeholder="bing,google,duckduckgo" onChange={e=>update(i,{engines:e.target.value})}/></label>}
    </div>
   </div>):<div className="rounded-2xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">{t('noEntries')}</div>}</div>
  </div>
  <button className="btn-secondary" onClick={add}>新增 SearXNG 实例</button>
  {msg&&<div className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-200">{msg}</div>}
 </div>
}

function SecretListManager({settingKey}:{settingKey:string}){
 const {t}=useLang()
 const [status,setStatus]=useState<any>(null)
 const [value,setValue]=useState('')
 const [busy,setBusy]=useState(false)
 async function load(){setStatus(await api(`/api/settings/secret-list/${settingKey}`))}
 useEffect(()=>{load().catch(()=>{})},[settingKey])
 async function add(){if(!value.trim()) return; setBusy(true); try{setStatus(await api('/api/settings/secret-list/append',{method:'POST',body:JSON.stringify({key:settingKey,value})})); setValue('')} finally{setBusy(false)}}
 async function remove(index:number){setBusy(true); try{setStatus(await api('/api/settings/secret-list/remove',{method:'POST',body:JSON.stringify({key:settingKey,index})}))} finally{setBusy(false)}}
 async function clear(){if(!confirm(t('clearAllConfirm'))) return; setBusy(true); try{setStatus(await api('/api/settings/secret-list/clear',{method:'POST',body:JSON.stringify({key:settingKey})}))} finally{setBusy(false)}}
 return <div className="space-y-3">
  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
   <div className="mb-3 flex items-center justify-between"><div><b>已配置 {status?.count||0} 条</b><p className="text-xs text-slate-500">{t('rotationHint')}</p></div><button className="btn-secondary" disabled={busy||!(status?.count)} onClick={clear}>{t('clearAll')}</button></div>
   <div className="space-y-2">{status?.items?.length?status.items.map((it:any)=><div className="flex items-center justify-between rounded-xl bg-slate-950 px-3 py-2 text-sm" key={it.index}><span>#{it.index+1}</span><code>{it.masked}</code><button className="btn-secondary" disabled={busy} onClick={()=>remove(it.index)}>{t('remove')}</button></div>):<div className="text-sm text-slate-500">{t('noEntries')}</div>}</div>
  </div>
  <div className="flex gap-2"><input className="input flex-1 font-mono text-sm" type="password" value={value} placeholder={t('pasteNewApiKey')} onChange={e=>setValue(e.target.value)}/><button className="btn" disabled={busy||!value.trim()} onClick={add}>{t('confirmAdd')}</button></div>
 </div>
}


function LLMPrimaryManager({settingFor, update}:{settingFor:(key:string)=>Setting; update:(key:string,patch:Partial<Setting>)=>void}){
 const [models,setModels]=useState<string[]>([])
 const [busy,setBusy]=useState(false)
 const [msg,setMsg]=useState('')
 const base=settingFor('LLM_PRIMARY_BASE_URL').value||''
 const key=settingFor('LLM_PRIMARY_API_KEY').value||''
 const model=settingFor('LLM_PRIMARY_MODEL').value||''
 async function loadModels(){
  setBusy(true); setMsg('正在获取模型列表...')
  try{
   const r=await api<any>('/api/settings/llm/models',{method:'POST',body:JSON.stringify({base_url:base,api_key:key.startsWith('***')?'':key})})
   if(r.ok){setModels(r.models||[]); setMsg(`✅ 获取到 ${r.count||0} 个模型`)} else {setMsg(`❌ ${r.error||'获取失败'}`)}
  }catch(e:any){setMsg(`❌ ${e.message}`)} finally{setBusy(false)}
 }
 return <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl shadow-black/10">
  <div className="mb-4"><h3 className="font-bold text-slate-100">主模型配置</h3><p className="mt-1 text-xs text-slate-500">填写兼容 OpenAI 的 Base URL 和 Key，然后自动获取模型列表选择。</p></div>
  <div className="grid gap-3 lg:grid-cols-2">
   <label className="block"><span className="mb-1 block text-xs text-slate-500">Base URL</span><input className="input font-mono text-sm" value={base} placeholder="https://api.openai.com/v1" onChange={e=>update('LLM_PRIMARY_BASE_URL',{value:e.target.value,secret:false})}/></label>
   <label className="block"><span className="mb-1 block text-xs text-slate-500">API Key</span><input className="input font-mono text-sm" type="password" value={key.startsWith('***')?'':key} placeholder={key.startsWith('***')?key:'sk-...'} onChange={e=>update('LLM_PRIMARY_API_KEY',{value:e.target.value,secret:true})}/></label>
  </div>
  <div className="mt-3 flex flex-wrap gap-2"><button className="btn-secondary" disabled={busy||!base.trim()} onClick={loadModels}>{busy?'获取中...':'获取模型列表'}</button>{msg&&<span className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-300">{msg}</span>}</div>
  <label className="mt-4 block"><span className="mb-1 block text-xs text-slate-500">模型</span>{models.length?<select className="input w-full" value={model} onChange={e=>update('LLM_PRIMARY_MODEL',{value:e.target.value,secret:false})}><option value="">请选择模型</option>{models.map(m=><option key={m} value={m}>{m}</option>)}</select>:<input className="input w-full font-mono text-sm" value={model} placeholder="先获取模型列表；也可手动填写" onChange={e=>update('LLM_PRIMARY_MODEL',{value:e.target.value,secret:false})}/>}</label>
 </div>
}

function LLMFallbackManager(){
 const [rows,setRows]=useState<any[]>([])
 const [modelsByIndex,setModelsByIndex]=useState<Record<number,string[]>>({})
 const [busy,setBusy]=useState(false)
 const [msg,setMsg]=useState('')
 async function load(){const r=await api<any>('/api/settings/llm/fallbacks'); setRows(r.items||[])}
 useEffect(()=>{load().catch(()=>{})},[])
 function add(){setRows([...rows,{base_url:'',model:'',api_key:''}])}
 function update(i:number,patch:any){setRows(rows.map((r,idx)=>idx===i?{...r,...patch}:r))}
 function remove(i:number){setRows(rows.filter((_,idx)=>idx!==i))}
 async function save(){
  setBusy(true); setMsg('')
  try{
   const fallbacks=rows.map(r=>({base_url:(r.base_url||r.provider||'').trim(),model:(r.model||'').trim(),api_key:(r.api_key||'').trim()})).filter(r=>r.base_url)
   const saved=await api<any>('/api/settings/llm/fallbacks',{method:'POST',body:JSON.stringify({fallbacks})})
   setRows(saved.items||[]); setMsg('✅ 已保存备用模型')
  }catch(e:any){setMsg(`❌ ${e.message}`)} finally{setBusy(false)}
 }
 async function loadModels(i:number){
  const row=rows[i]
  setBusy(true); setMsg(`正在获取 #${i+1} 模型列表...`)
  try{
   const r=await api<any>('/api/settings/llm/models',{method:'POST',body:JSON.stringify({base_url:(row.base_url||row.provider||''),api_key:(row.api_key||'').startsWith('***')?'':(row.api_key||''),fallback_index:i})})
   if(r.ok){setModelsByIndex({...modelsByIndex,[i]:r.models||[]}); setMsg(`✅ #${i+1} 获取到 ${r.count||0} 个模型`)} else {setMsg(`❌ #${i+1} ${r.error||'获取失败'}`)}
  }catch(e:any){setMsg(`❌ ${e.message}`)} finally{setBusy(false)}
 }
 return <div className="space-y-3 rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl shadow-black/10">
  <div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-bold text-slate-100">备用模型</h3><p className="mt-1 text-xs text-slate-500">每个 fallback 都填写 Base URL 和 Key，然后自动获取模型列表选择。</p></div><button className="btn" disabled={busy} onClick={save}>{busy?'保存中...':'保存备用模型'}</button></div>
  <div className="space-y-3">{rows.length?rows.map((row,i)=>{const list=modelsByIndex[i]||[]; return <div key={i} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
   <div className="mb-3 flex items-center justify-between"><span className="text-sm text-slate-500">Fallback #{i+1}</span><button className="btn-secondary" onClick={()=>remove(i)}>删除</button></div>
   <div className="grid gap-3 lg:grid-cols-2">
    <label className="block"><span className="mb-1 block text-xs text-slate-500">Base URL</span><input className="input font-mono text-sm" value={row.base_url||row.provider||''} placeholder="https://api.openai.com/v1" onChange={e=>update(i,{base_url:e.target.value,provider:e.target.value})}/></label>
    <label className="block"><span className="mb-1 block text-xs text-slate-500">API Key</span><input className="input font-mono text-sm" type="password" value={(row.api_key||'').startsWith('***')?'':(row.api_key||'')} placeholder={(row.api_key||'').startsWith('***')?row.api_key:'sk-...'} onChange={e=>update(i,{api_key:e.target.value})}/></label>
   </div>
   <div className="mt-3 flex flex-wrap gap-2"><button className="btn-secondary" disabled={busy||!(row.base_url||row.provider||'').trim()} onClick={()=>loadModels(i)}>获取模型列表</button></div>
   <label className="mt-3 block"><span className="mb-1 block text-xs text-slate-500">模型</span>{list.length?<select className="input w-full" value={row.model||''} onChange={e=>update(i,{model:e.target.value})}><option value="">请选择模型</option>{list.map(m=><option key={m} value={m}>{m}</option>)}</select>:<input className="input font-mono text-sm" value={row.model||''} placeholder="先获取模型列表；也可手动填写" onChange={e=>update(i,{model:e.target.value})}/>}</label>
  </div>}) : <div className="rounded-2xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">暂无备用模型</div>}</div>
  <button className="btn-secondary" onClick={add}>新增备用模型</button>
  {msg&&<div className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-300">{msg}</div>}
 </div>
}

export function SettingsForm({rows, initialGroup='search'}:{rows:any[]; initialGroup?:string}){
 const {t}=useLang()
 const [items,setItems]=useState<Setting[]>(rows)
 const [active,setActive]=useState(initialGroup)
 const [msg,setMsg]=useState('')
 const [dirty,setDirty]=useState(false)
 const [saving,setSaving]=useState(false)
 const [testing,setTesting]=useState(false)
 const [currentPassword,setCurrentPassword]=useState('')
 const [newPassword,setNewPassword]=useState('')
 const [pendingAdd,setPendingAdd]=useState<Record<string,string>>({})
 const byKey=useMemo(()=>Object.fromEntries(items.map((x:any)=>[x.key,x])),[items])
 useEffect(()=>{setActive(initialGroup||'search')},[initialGroup])
 const group=GROUPS.find(g=>g.id===active)||GROUPS[0]
 function settingFor(key:string):Setting{return byKey[key]||{key,value:'',secret:SECRET_KEYS.includes(key)}}
 function update(key:string, patch:Partial<Setting>){setDirty(true); setItems(items.map((x:any)=>x.key===key?{...x,...patch}:x).concat(byKey[key]?[]:[{key,value:'',secret:SECRET_KEYS.includes(key),...patch} as Setting]))}
 async function saveGroup(keys:string[]){setSaving(true); try{for(const k of keys){if(k==='SEARXNG_ENDPOINTS') continue; const s=settingFor(k); if(s.secret&&masked(s.value)) continue; await api('/api/settings',{method:'POST',body:JSON.stringify(s)})} setDirty(false); setMsg(`${t('saved')} ${group.title||t(group.titleKey)}`)} finally{setSaving(false)}}
  async function test(){setTesting(true);setMsg(t('testing')); try{const r=await api<any>('/api/settings/test-search',{method:'POST'}); const p=r.providers||{}; setMsg(r.ok?`✅ ${t('searchOk')}: ${r.result_count} results, ${r.elapsed_ms}ms · providers=${(p.available||[]).join(',')||'none'} · searxng=${p.searxng_urls||0} · braveKeys=${p.brave_keys||0} · tavilyKeys=${p.tavily_keys||0}`:`❌ ${t('searchFailed')}: ${r.error}`)}catch(e:any){setMsg(`❌ ${e.message}`)} finally{setTesting(false)}}
 async function changePassword(){setMsg(t('changingPassword')); try{await api('/api/auth/password',{method:'POST',body:JSON.stringify({current_password:currentPassword,new_password:newPassword})}); setCurrentPassword(''); setNewPassword(''); setMsg(`✅ ${t('passwordChanged')}`)}catch(e:any){setMsg(`❌ ${e.message}`)}}
 function setListItem(key:string, idx:number, value:string){const xs=splitList(settingFor(key).value); xs[idx]=value; update(key,{value:joinList(xs)})}
 function addListItem(key:string){const cur=settingFor(key).value||''; update(key,{value:cur+(cur.trim()?'\n':'')})}
 function removeListItem(key:string, idx:number){const xs=splitList(settingFor(key).value); xs.splice(idx,1); update(key,{value:joinList(xs)})}
 return <div className="grid gap-6 xl:grid-cols-[300px_1fr]">
  <aside className="panel h-fit xl:sticky xl:top-6">
   <div className="mb-3 px-2 text-xs font-bold uppercase tracking-[0.25em] text-slate-500">{t('settingsMenu')}</div>
   <nav className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:block xl:space-y-2">
   {GROUPS.map(g=><Link href={`/settings/${g.id}`} key={g.id} onClick={()=>setActive(g.id)} className={`block w-full rounded-2xl px-4 py-3 text-left no-underline transition ${active===g.id?'bg-blue-600/20 text-blue-100 ring-1 ring-blue-500/50':'bg-slate-950/50 text-slate-300 hover:bg-slate-900'}`}><div className="font-bold">{g.title||t(g.titleKey)}</div><div className="mt-1 text-xs leading-5 text-slate-500">{g.desc||t(g.descKey)}</div></Link>)}
   </nav>
  </aside>
  <main className="space-y-5">
   <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-6 shadow-2xl">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><div className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">{t('configuration')}</div><h2 className="mt-2 text-3xl font-black">{group.title||t(group.titleKey)}</h2><p className="mt-1 text-sm text-slate-400">{group.desc||t(group.descKey)}</p></div><div className="flex gap-2">{['search','searxng'].includes(active)&&<><button className="btn-secondary" disabled={testing} onClick={test}>{testing?t('testing'):t('testProviders')}</button></>}{group.keys.filter((k:string)=>k!=='SEARXNG_ENDPOINTS').length>0&&<><span className={`badge ${dirty?'badge-watch':'badge-action'}`}>{saving?t('saving'):(dirty?t('unsaved'):t('savedState'))}</span><button className="btn" disabled={saving||!dirty} onClick={()=>saveGroup(group.keys)}>{t('saveGroup')}</button></>}</div></div>
    {msg&&<div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-200">{msg}</div>}{['search','searxng'].includes(active)&&<div className="mt-5"><ProviderHealthPanel/></div>}
   </section>
   {active==='security'?<section className="panel space-y-4"><h3 className="text-xl font-bold">{t('changePassword')}</h3><div className="grid gap-3 md:grid-cols-2"><input className="input" type="password" placeholder={t('currentPassword')} value={currentPassword} onChange={e=>setCurrentPassword(e.target.value)}/><input className="input" type="password" placeholder={t('newPassword')} value={newPassword} onChange={e=>setNewPassword(e.target.value)}/></div><button className="btn" disabled={!newPassword||newPassword.length<8} onClick={changePassword}>{t('updatePassword')}</button></section>:active==='llm'?<section className="space-y-4"><LLMPrimaryManager settingFor={settingFor} update={update}/><LLMFallbackManager/></section>:<section className="space-y-4">{group.keys.map((key:string)=>renderSetting(key))}</section>}
  </main>
 </div>

 function renderSetting(key:string){const s=settingFor(key); const bool=BOOL_KEYS.includes(key); const list=LIST_KEYS.includes(key); const multi=MULTILINE_KEYS.includes(key); const values=splitList(s.value); const fallback=key==='LLM_FALLBACKS'; return <div key={key} className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl shadow-black/10"><div className="mb-4 flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><h3 className="font-bold text-slate-100">{KEY_LABELS[key]||key}</h3>{SECRET_KEYS.includes(key)&&s.secret&&<span className="badge">{t('secret')}</span>}{list&&<span className="badge badge-action">{t('rotation')}</span>}</div><div className="mt-1 font-mono text-xs text-slate-600">{key}</div><div className="mt-1 text-xs text-slate-500">{s.updated_at?new Date(s.updated_at).toLocaleString():t('notSaved')}</div>{list&&<p className="mt-2 text-xs text-blue-300">{t('rotationHint')}</p>}{fallback&&<p className="mt-2 text-xs text-blue-300">{t('fallbackHint')}</p>}</div>{SECRET_KEYS.includes(key)&&key!=='SEARXNG_ENDPOINTS'&&<div className="flex gap-2"><label className="flex items-center gap-2 text-xs text-slate-400"><input type="checkbox" checked={!!s.secret} onChange={e=>update(key,{secret:e.target.checked})}/> {t('secret')}</label></div>}</div>{bool?<select className="input w-full" value={s.value||'false'} onChange={e=>update(key,{value:e.target.value})}><option value="true">开启</option><option value="false">关闭</option></select>:key==='SEARXNG_ENDPOINTS'?<SearxngEndpointManager/>:list&&['BRAVE_API_KEYS','TAVILY_API_KEYS'].includes(key)?<SecretListManager settingKey={key}/>:list?<div className="space-y-3"><div className="space-y-2">{values.length?values.map((v,i)=><div key={i} className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/60 p-3"><div className="flex-1 font-mono text-sm text-slate-200">{masked(v)?v:v}</div><button className="btn-secondary" onClick={()=>removeListItem(key,i)}>{t('remove')}</button></div>):<div className="rounded-2xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">{t('noEntries')}</div>}</div><div className="flex gap-2"><input className="input flex-1 font-mono text-sm" type={s.secret?'password':'text'} value={pendingAdd[key]||''} placeholder={t('pasteNewApiKey')} onChange={e=>setPendingAdd({...pendingAdd,[key]:e.target.value})}/><button className="btn" disabled={!(pendingAdd[key]||'').trim()} onClick={()=>{const xs=splitList(s.value); xs.push((pendingAdd[key]||'').trim()); update(key,{value:joinList(xs)}); setPendingAdd({...pendingAdd,[key]:''})}}>{t('confirmAdd')}</button></div><textarea className="input min-h-24 w-full font-mono text-xs" value={s.value||''} onChange={e=>update(key,{value:e.target.value})} placeholder={t('pasteBulk')}/></div>:fallback?<LLMFallbackManager/>:multi?<textarea className="input min-h-28 w-full font-mono text-sm" value={s.value||''} onChange={e=>update(key,{value:e.target.value})}/>:<input className="input w-full" type={s.secret?'password':'text'} value={masked(s.value)?'':s.value||''} placeholder={masked(s.value)?s.value:''} onChange={e=>update(key,{value:e.target.value})}/>}</div>}
}
