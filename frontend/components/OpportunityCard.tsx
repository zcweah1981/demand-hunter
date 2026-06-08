import {ExportCardMarkdownButton, Feedback} from './Actions'
import {I18nText} from './I18nText'

export function verdictClass(v:string){return v==='Action'?'badge badge-action':v==='Watch'?'badge badge-watch':'badge badge-reject'}
export function verdictLabel(v:string){return v==='Action'?'行动 Action':v==='Watch'?'观察 Watch':v==='Reject'?'拒绝 Reject':v==='Block'?'屏蔽 Block':v}
function evidenceTypeLabel(t:string){const m:any={business:'商业判断',serp:'搜索结果',social:'社媒证据',competitor:'竞品',keyword:'关键词',source:'来源',url:'链接',error:'错误'}; return m[t]||t}
function shortText(s:string,n=180){s=(s||'').replace(/\s+/g,' ').trim(); return s.length>n?s.slice(0,n)+'…':s}

export function OpportunityCardView({card,compact=false,showFeedback=true,onFeedback,mode='review'}:{card:any;compact?:boolean;showFeedback?:boolean;onFeedback?:(label:string)=>void;mode?:'review'|'execute'}){
 const allEvidence=card.evidence_json||[]
 const business=allEvidence.find((e:any)=>e.type==='business')
 const evidence=allEvidence.filter((e:any)=>e.type!=='business')
 const topEvidence=evidence.slice(0,2)
 const labels:any={Demand:'需求强度',SERP:'搜索缺口',Weakness:'竞品弱点',Commercial:'MVP 可行性',Money:'变现潜力'}
 return <article className="card safe-text space-y-4">
  <div className="flex flex-wrap items-start justify-between gap-3">
   <div className="min-w-0">
    <h2 className="text-lg font-semibold text-white">{card.title}</h2>
    <p className="mt-1 text-sm text-slate-400"><span className="text-slate-500">变现类型：</span>{business?.business_type||card.monetization_type||'未标注'}</p>
   </div>
   <div className="flex shrink-0 flex-col items-end gap-2">
    <span className={verdictClass(card.verdict)}>{verdictLabel(card.verdict)} · {card.score}</span>
    {business?.go_no_go&&<span className="badge badge-watch">商业判断：{business.go_no_go} · {Math.round((business.commercial_score||0)*100)}</span>}
    {!compact&&<ExportCardMarkdownButton id={card.id}/>} 
   </div>
  </div>

  {showFeedback&&!compact&&mode==='review'&&<div className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-3">
   <div className="mb-2 text-xs font-semibold tracking-wide text-blue-200">复核决策</div>
   <div className="flex flex-wrap items-center justify-between gap-3">
    <span className="text-xs text-slate-400">优先按证据与风险判断：Action / Watch / Reject / Block</span>
    {onFeedback?<InlineFeedback onFeedback={onFeedback}/>:<Feedback id={card.id}/>} 
   </div>
  </div>}

  <div className="grid grid-cols-2 gap-2 text-xs text-slate-300 sm:grid-cols-3 lg:grid-cols-5">
   {[['Demand',card.demand_score],['SERP',card.serp_gap_score],['Weakness',card.competitor_weakness_score],['Commercial',card.mvp_score],['Money',card.monetization_score]].map(([k,v])=><div className="rounded-xl bg-slate-950/80 p-2" key={k as string}><div className="text-slate-500">{labels[k as string]}</div><b>{v as any}</b></div>)}
  </div>

  {!compact&&mode==='execute'&&business&&<section className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4">
   <div className="mb-3 text-xs font-semibold tracking-wide text-emerald-200">执行摘要</div>
   <div className="grid gap-3 text-sm text-slate-200 md:grid-cols-2">
    <div><b>第一步验证</b><ol className="mt-1 list-decimal pl-5 text-slate-300">{(business.first_sale_test||[]).slice(0,3).map((x:string)=><li key={x}>{x}</li>)}</ol>{!business.first_sale_test?.length&&<p className="mt-1 text-slate-400">{shortText(business.commercial_mvp,220)||shortText(card.mvp_plan,220)||'-'}</p>}</div>
    <div><b>最小商业 MVP</b><p className="mt-1 text-slate-400">{shortText(business.commercial_mvp,240)||shortText(card.mvp_plan,240)||'-'}</p></div>
    <div><b>收入路径 / 定价</b><p className="mt-1 text-slate-400">{shortText(business.revenue_path,160)||'-'}{business.pricing?` · ${shortText(business.pricing,120)}`:''}</p></div>
    <div><b>获客 / 切入点</b><p className="mt-1 text-slate-400">{shortText(business.gtm,150)||'-'}{business.wedge?` · ${shortText(business.wedge,120)}`:''}</p></div>
   </div>
   {business.key_assumption&&<p className="mt-3 rounded-xl bg-slate-950/70 p-3 text-xs text-slate-300"><b>关键假设：</b>{shortText(business.key_assumption,260)}</p>}
  </section>}

  {!compact&&mode==='review'&&business&&<section className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
   <div className="mb-3 text-xs font-semibold tracking-wide text-slate-500">决策摘要</div>
   {business.verdict_reason&&<p className="mb-3 text-sm leading-6 text-slate-200"><b>判断理由：</b>{shortText(business.verdict_reason,260)}</p>}
   {business.missing_evidence?.length>0&&<div className="mb-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100"><b>待补证据：</b>{business.missing_evidence.join('、')}</div>}
   <div className="grid gap-3 text-sm text-slate-300 md:grid-cols-2">
    <div><b className="text-slate-100">目标用户</b><p className="mt-1 text-slate-400">{shortText(business.icp,160)||'-'}</p></div>
    <div><b className="text-slate-100">付费触发</b><p className="mt-1 text-slate-400">{shortText(business.pay_trigger,160)||'-'}</p></div>
    <div><b className="text-slate-100">最小商业 MVP</b><p className="mt-1 text-slate-400">{shortText(business.commercial_mvp,180)||shortText(card.mvp_plan,180)||'-'}</p></div>
    <div><b className="text-slate-100">收入路径</b><p className="mt-1 text-slate-400">{shortText(business.revenue_path,160)||card.monetization_type||'-'}</p></div>
   </div>
  </section>}

  {card.risks?.length>0&&<div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3"><div className="mb-1 text-xs font-semibold text-amber-200">风险</div><ul className="list-disc pl-5 text-xs text-amber-100/90">{card.risks.slice(0,compact?2:4).map((r:string)=><li key={r}>{r}</li>)}</ul>{!compact&&card.risks.length>4&&<p className="mt-1 text-xs text-amber-100/70">另有 {card.risks.length-4} 条风险，见完整详情。</p>}</div>}

  {!compact&&topEvidence.length>0&&<div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3"><div className="mb-2 text-xs font-semibold tracking-wide text-slate-500">关键证据摘要</div><div className="space-y-1">{topEvidence.map((e:any,i:number)=><a key={i} className="block truncate text-xs text-blue-300 hover:text-blue-200" href={e.url} target="_blank">[{evidenceTypeLabel(e.type)}] {e.title}</a>)}</div></div>}

  {!compact&&<details className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
   <summary className="cursor-pointer text-sm font-semibold text-slate-300 hover:text-white">展开完整商业分析 / MVP / 全部证据</summary>
   {business&&<section className="mt-4 rounded-2xl border border-blue-500/30 bg-blue-500/10 p-4">
    <div className="mb-3 text-xs font-semibold tracking-wide text-blue-200">商业化判断 <span className="text-blue-300/60">Commercialization Brief</span></div>
    <div className="mb-3 flex flex-wrap gap-2 text-xs">
     {business.keyword_type&&<span className="badge">词类型：{business.keyword_type}</span>}
     {business.seo_fit&&<span className="badge badge-action">SEO 适配：{business.seo_fit}</span>}
     {business.analysis_source&&<span className="badge badge-watch">分析来源：{business.analysis_source}</span>}
    </div>
    <div className="grid gap-3 text-sm text-slate-200 md:grid-cols-2">
     <div><b>目标用户 <span className="text-slate-500">ICP</span></b><p className="mt-1 text-slate-400">{business.icp}</p></div>
     <div><b>付费触发 <span className="text-slate-500">Pay Trigger</span></b><p className="mt-1 text-slate-400">{business.pay_trigger}</p></div>
     <div><b>快速商业 MVP <span className="text-slate-500">Commercial MVP</span></b><p className="mt-1 text-slate-400">{business.commercial_mvp}</p></div>
     <div><b>收入路径 <span className="text-slate-500">Revenue Path</span></b><p className="mt-1 text-slate-400">{business.revenue_path}</p></div>
     <div><b>定价 <span className="text-slate-500">Pricing</span></b><p className="mt-1 text-slate-400">{business.pricing}</p></div>
     <div><b>获客方式 <span className="text-slate-500">GTM</span></b><p className="mt-1 text-slate-400">{business.gtm}</p></div>
     <div><b>切入点 <span className="text-slate-500">Wedge</span></b><p className="mt-1 text-slate-400">{business.wedge}</p></div>
    </div>
    {business.first_sale_test?.length>0&&<div className="mt-3"><b className="text-sm">第一笔钱测试 <span className="text-slate-500">First Sale Test</span></b><ol className="mt-2 list-decimal pl-5 text-xs text-slate-300">{business.first_sale_test.map((x:string)=><li key={x}>{x}</li>)}</ol></div>}
    {business.key_assumption&&<p className="safe-text mt-3 rounded-xl bg-slate-950/70 p-3 text-xs text-slate-300"><b>关键假设：</b>{business.key_assumption}</p>}
   </section>}
   {card.mvp_plan&&<div className="safe-text mt-4 text-sm leading-6 text-slate-300"><div className="mb-1 text-xs font-semibold text-slate-500">MVP 计划</div>{card.mvp_plan}</div>}
   {evidence.length>0&&<div className="mt-4"><div className="mb-2 text-xs font-semibold tracking-wide text-slate-500">全部证据 Evidence</div><div className="space-y-1">{evidence.map((e:any,i:number)=><a key={i} className="block truncate text-xs text-blue-300 hover:text-blue-200" href={e.url} target="_blank">[{evidenceTypeLabel(e.type)}] {e.title}</a>)}</div></div>}
  </details>}

  {showFeedback&&compact&&<div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-3">
   <span className="text-xs text-slate-500">复核反馈会训练词根和屏蔽词</span>
   {onFeedback?<InlineFeedback onFeedback={onFeedback}/>:<Feedback id={card.id}/>} 
  </div>}
 </article>
}

function InlineFeedback({onFeedback}:{onFeedback:(label:string)=>void}){const labels:any={Action:'行动',Watch:'观察',Reject:'拒绝',Block:'屏蔽'}; return <div className="flex flex-wrap gap-2">{['Action','Watch','Reject','Block'].map(x=><button key={x} title={x} className="rounded bg-slate-800 px-2 py-1 text-xs hover:bg-slate-700" onClick={()=>onFeedback(x)}>{labels[x]} <span className="text-slate-500">{x}</span></button>)}</div>}
