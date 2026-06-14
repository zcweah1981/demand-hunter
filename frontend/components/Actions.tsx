'use client'
import {useState} from 'react'
import {api, authToken, automationCycleApi, submitAction} from '../lib/api'
import {useLang} from '../lib/i18n'

function useRun(){
  const[loading,setLoading]=useState(false)
  const[err,setErr]=useState('')
  const[msg,setMsg]=useState('')
  return {loading,setLoading,err,setErr,msg,setMsg}
}

function InlineStatus({s}:{s:ReturnType<typeof useRun>}){
  return <>{s.err&&<span className="mr-2 text-sm text-red-400">{s.err}</span>}{s.msg&&<span className="mr-2 text-sm text-slate-400">{s.msg}</span>}</>
}

export function RunDailyButton(){
  const s=useRun()
  const {lang}=useLang()
  return <span><InlineStatus s={s}/><button className="btn" disabled={s.loading} onClick={async()=>{
    s.setLoading(true)
    s.setErr('')
    s.setMsg(lang==='en'?'Automation cycle is starting; see the top status bar.':'自动化周期正在启动，请查看顶部状态栏。')
    try{
      await automationCycleApi.run({limit:24})
      s.setMsg(lang==='en'?'Automation cycle started. The top status bar will continue tracking progress.':'自动化周期已启动，顶部状态栏会继续显示进度。')
      setTimeout(()=>location.reload(),800)
    }catch(e:any){
      s.setErr(e.message)
      s.setLoading(false)
    }
  }}>{s.loading?(lang==='en'?'Starting...':'启动中...'):(lang==='en'?'Run Automation Cycle':'运行自动化周期')}</button></span>
}

export function AutoTickButton(){
  const s=useRun()
  const {lang}=useLang()
  return <span><InlineStatus s={s}/><button className="btn" disabled={s.loading} onClick={async()=>{
    s.setLoading(true)
    s.setErr('')
    s.setMsg(lang==='en'?'Automation cycle is starting; see the top status bar.':'自动化周期正在启动，请查看顶部状态栏。')
    try{
      await automationCycleApi.run({force:true})
      s.setMsg(lang==='en'?'Automation cycle started. The top status bar will continue tracking progress.':'自动化周期已启动，顶部状态栏会继续显示进度。')
      setTimeout(()=>location.reload(),800)
    }catch(e:any){
      s.setErr(e.message)
      s.setLoading(false)
    }
  }}>{s.loading?(lang==='en'?'Starting...':'启动中...'):(lang==='en'?'Run Now':'现在跑一轮')}</button></span>
}

export function DiscoverButton(){
  const s=useRun()
  const {lang}=useLang()
  return <span><InlineStatus s={s}/><button className="btn" disabled={s.loading} onClick={async()=>{
    s.setLoading(true)
    s.setErr('')
    s.setMsg(lang==='en'?'Clue model action submitted.':'线索模型动作已提交，顶部状态栏会显示进度。')
    try{
      await submitAction({action_type:'clue_model.run',target_type:'clue_model',target_id:'all',reason:'手动发现线索',payload:{model:'all',limit:48}},false)
      await automationCycleApi.run({include_default_actions:false, background:false})
      s.setMsg(lang==='en'?'Discovery action finished.':'发现动作已完成。')
      setTimeout(()=>location.reload(),800)
    }catch(e:any){
      s.setErr(e.message)
      s.setLoading(false)
    }
  }}>{s.loading?(lang==='en'?'Submitting...':'提交中...'):(lang==='en'?'Run Clue Models':'运行线索模型')}</button></span>
}

export function SerpButton({id}:{id:number}){
  const s=useRun()
  const {lang}=useLang()
  return <span><InlineStatus s={s}/><button className="btn" disabled={s.loading} onClick={async()=>{
    s.setLoading(true)
    s.setErr('')
    s.setMsg(lang==='en'?'SERP action submitted.':'SERP 分析动作已提交。')
    try{
      await submitAction({action_type:'keyword.serp_analysis',target_type:'keyword',target_id:id,reason:'手动触发关键词搜索分析'})
      s.setMsg(lang==='en'?'SERP action finished.':'SERP 分析已完成。')
      setTimeout(()=>location.reload(),800)
    }catch(e:any){
      s.setErr(e.message)
      s.setLoading(false)
    }
  }}>{s.loading?(lang==='en'?'Running...':'运行中...'):(lang==='en'?'Run SERP':'运行 SERP')}</button></span>
}

export function CardButton({id}:{id:number}){
  const s=useRun()
  const {lang}=useLang()
  return <span><InlineStatus s={s}/><button className="btn" disabled={s.loading} onClick={async()=>{
    s.setLoading(true)
    s.setErr('')
    s.setMsg(lang==='en'?'Opportunity generation action submitted.':'机会生成动作已提交。')
    try{
      await submitAction({action_type:'opportunity.generate',target_type:'keyword',target_id:id,reason:'手动生成机会'})
      s.setMsg(lang==='en'?'Opportunity action finished.':'机会生成已完成。')
      setTimeout(()=>location.reload(),800)
    }catch(e:any){
      s.setErr(e.message)
      s.setLoading(false)
    }
  }}>{s.loading?(lang==='en'?'Generating...':'生成中...'):(lang==='en'?'Generate Opportunity':'生成机会')}</button></span>
}
function fbClass(x:string){const m:any={Watch:'border-blue-500/40 bg-blue-500/10 text-blue-200 hover:bg-blue-500/20',Action:'border-emerald-500/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20',Adopted:'border-purple-500/40 bg-purple-500/10 text-purple-200 hover:bg-purple-500/20',Reject:'border-amber-500/40 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20',Block:'border-rose-500/40 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20'}; return `rounded border px-2 py-1 text-xs ${m[x]}`}
export function Feedback({id}:{id:number}){const labels:any={Adopted:'采纳',Action:'行动',Watch:'观察',Reject:'拒绝',Block:'屏蔽'}; return <div className="flex flex-wrap gap-2">{['Adopted','Action','Watch','Reject','Block'].map(x=><button key={x} title={x} className={fbClass(x)} onClick={async()=>{await api(`/api/cards/${id}/feedback`,{method:'POST',body:JSON.stringify({label:x})}); location.reload()}}>{labels[x]} <span className="opacity-60">{x}</span></button>)}</div>}
export function ExportReportButton(){const[loading,setLoading]=useState(false); const {lang}=useLang(); return <button className="btn" disabled={loading} onClick={async()=>{setLoading(true); try{const token=authToken(); const res=await fetch('/api/reports/download/latest',{headers:token?{Authorization:`Bearer ${token}`}:{}}); if(!res.ok) throw new Error(`${res.status} ${await res.text()}`); const blob=await res.blob(); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='demand_cards_latest.md'; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)}catch(e:any){alert(e.message)} finally{setLoading(false)}}}>{loading?(lang==='en'?'Downloading...':'下载中...'):(lang==='en'?'Download Daily Digest':'下载日报')}</button>}
export function ExportActionsButton(){const[loading,setLoading]=useState(false); return <button className="btn" disabled={loading} onClick={async()=>{setLoading(true); try{const token=authToken(); const res=await fetch('/api/reports/download/actions',{headers:token?{Authorization:`Bearer ${token}`}:{}}); if(!res.ok) throw new Error(`${res.status} ${await res.text()}`); const blob=await res.blob(); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='action_execution_list.md'; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)}catch(e:any){alert(e.message)} finally{setLoading(false)}}}>{loading?'下载中...':'下载执行清单'}</button>}
export function ExportCardMarkdownButton({id}:{id:number}){const[loading,setLoading]=useState(false); return <button className="btn-secondary" disabled={loading} onClick={async()=>{setLoading(true); try{const token=authToken(); const res=await fetch(`/api/cards/${id}/markdown`,{headers:token?{Authorization:`Bearer ${token}`}:{}}); if(!res.ok) throw new Error(`${res.status} ${await res.text()}`); const blob=await res.blob(); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=`opportunity-card-${id}.md`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)}catch(e:any){alert(e.message)} finally{setLoading(false)}}}>{loading?'下载中...':'导出 Markdown'}</button>}
export function ReanalyzeCardButton({id}:{id:number}){const[loading,setLoading]=useState(false); return <button className="btn-secondary" disabled={loading} onClick={async()=>{if(!confirm('重新生成这张机会的商业分析？状态不会被覆盖。')) return; setLoading(true); try{await api(`/api/cards/${id}/reanalyze`,{method:'POST'}); location.reload()}catch(e:any){alert(e.message); setLoading(false)}}}>{loading?'分析中...':'重新 LLM 分析'}</button>}
export function CreateProgressButton({id}:{id:number}){const[loading,setLoading]=useState(false); return <button className="btn" disabled={loading} onClick={async()=>{setLoading(true); try{const r:any=await api(`/api/progress/from-card/${id}`,{method:'POST'}); location.href=`/hunter/progress?project=${r.project?.id||''}`}catch(e:any){alert(e.message); setLoading(false)}}}>{loading?'创建中...':'创建推进项目'}</button>}
function riskText(action:any){const flags=action.manual_flags||[]; const lines=[]; if(flags.includes('cooldown')) lines.push(`⚠️ 这项刚实验过，仍在冷却期内${action.cooldown_until?`（到 ${action.cooldown_until}）`:''}；重复执行可能污染效果评估。`); if(flags.includes('history_hidden')) lines.push('⚠️ 这项历史效果较差，系统已降低/隐藏推荐；请确认你要手动覆盖。'); return lines.join('\n')}
export function RepairActionButton({action}:{action:{label:string;action:string;source?:string;safety?:string;manual_flags?:string[];cooldown_until?:string}}){const[loading,setLoading]=useState(false); return <button className="rounded-lg bg-slate-800 px-2 py-1 text-xs text-slate-200 hover:bg-slate-700 disabled:opacity-50" title={action.safety||''} disabled={loading} onClick={async()=>{const risk=riskText(action); if(!confirm(`${action.label}\n\n${risk?`${risk}\n\n`:''}${action.safety||'仅修改内部设置，可逆。'}`)) return; setLoading(true); try{const r=await api<any>('/api/autopilot/repair',{method:'POST',body:JSON.stringify({action:action.action,source:action.source})}); if(!r.ok) alert(r.error||'repair failed'); location.reload()}catch(e:any){alert(e.message); setLoading(false)}}}>{loading?'处理中...':action.label}</button>}
export function RollbackRepairButton({id}:{id:number}){const[loading,setLoading]=useState(false); return <button className="rounded-lg bg-rose-950/60 px-2 py-1 text-xs text-rose-200 hover:bg-rose-900 disabled:opacity-50" disabled={loading} onClick={async()=>{if(!confirm(`回滚 repair #${id}？\n\n这会把对应 settings 恢复到修复前。`)) return; setLoading(true); try{const r=await api<any>('/api/autopilot/repair/rollback',{method:'POST',body:JSON.stringify({repair_id:id})}); if(!r.ok) alert(r.error||'rollback failed'); location.reload()}catch(e:any){alert(e.message); setLoading(false)}}}>{loading?'回滚中...':'回滚'}</button>}
export function ExperimentRepairButton({action}:{action:{label:string;action:string;source?:string;safety?:string;manual_flags?:string[];cooldown_until?:string}}){const[loading,setLoading]=useState(false); return <button className="rounded-lg bg-blue-950/70 px-2 py-1 text-xs text-blue-100 hover:bg-blue-900 disabled:opacity-50" disabled={loading} title="执行一个 repair，然后强制跑一轮，用下一轮 quality_report 评估效果" onClick={async()=>{const risk=riskText(action); if(!confirm(`${action.label}\n\n${risk?`${risk}\n\n`:''}自动实验会：\n1. 只执行这个 repair\n2. 立即跑一轮 daily run\n3. 用修复前后漏斗评估效果`)) return; setLoading(true); try{const r=await api<any>('/api/autopilot/experiment/start',{method:'POST',body:JSON.stringify({action:action.action,source:action.source,force_run:true})}); if(!r.ok){alert(r.error==='active_experiment_exists'?(r.message||'已有实验等待评估，请先处理。'):(r.error||'experiment failed')); setLoading(false); return} location.reload()}catch(e:any){alert(e.message); setLoading(false)}}}>{loading?'实验中...':'实验运行'}</button>}
export function RecommendedExperimentButton({action}:{action:{label:string;action:string;source?:string;safety?:string}}){const[loading,setLoading]=useState(false); return <button className="btn" disabled={loading} title={action.label} onClick={async()=>{if(!confirm(`运行推荐实验？\n\n系统将只执行一个推荐修复，并立即跑一轮评估效果。\n\n推荐项：${action.label}`)) return; setLoading(true); try{const r=await api<any>('/api/autopilot/experiment/start',{method:'POST',body:JSON.stringify({action:action.action,source:action.source,force_run:true})}); if(!r.ok){alert(r.error==='active_experiment_exists'?(r.message||'已有实验等待评估，请先处理。'):(r.error||'experiment failed')); setLoading(false); return} location.reload()}catch(e:any){alert(e.message); setLoading(false)}}}>{loading?'运行中...':'运行推荐实验'}</button>}
export function AbandonExperimentButton({id,rollback}:{id:number;rollback?:boolean}){const[loading,setLoading]=useState(false); return <button className={rollback?"rounded-lg bg-rose-950/60 px-2 py-1 text-xs text-rose-200 hover:bg-rose-900 disabled:opacity-50":"rounded-lg bg-slate-800 px-2 py-1 text-xs text-slate-200 hover:bg-slate-700 disabled:opacity-50"} disabled={loading} onClick={async()=>{if(!confirm(`${rollback?'放弃并回滚':'放弃'} experiment #${id}？`)) return; setLoading(true); try{const r=await api<any>('/api/autopilot/experiment/abandon',{method:'POST',body:JSON.stringify({experiment_id:id,rollback:!!rollback})}); if(!r.ok) alert(r.error||'abandon failed'); location.reload()}catch(e:any){alert(e.message); setLoading(false)}}}>{loading?'处理中...':rollback?'放弃并回滚':'放弃'}</button>}
