import {Feedback} from './Actions'
import {I18nText} from './I18nText'

export function verdictClass(v:string){return v==='Action'?'badge badge-action':v==='Watch'?'badge badge-watch':'badge badge-reject'}
export function verdictLabel(v:string){return v==='Action'?'行动 Action':v==='Watch'?'观察 Watch':v==='Reject'?'拒绝 Reject':v==='Block'?'屏蔽 Block':v}
function evidenceTypeLabel(t:string){const m:any={business:'商业判断',serp:'搜索结果',social:'社媒证据',competitor:'竞品',keyword:'关键词',source:'来源',url:'链接',error:'错误'}; return m[t]||t}

export function OpportunityCardView({card,compact=false,showFeedback=true}:{card:any;compact?:boolean;showFeedback?:boolean}){
 const allEvidence=card.evidence_json||[]
 const business=allEvidence.find((e:any)=>e.type==='business')
 const evidence=allEvidence.filter((e:any)=>e.type!=='business').slice(0,compact?2:5)
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
   </div>
  </div>

  <div className="grid grid-cols-2 gap-2 text-xs text-slate-300 sm:grid-cols-3 lg:grid-cols-5">
   {[['Demand',card.demand_score],['SERP',card.serp_gap_score],['Weakness',card.competitor_weakness_score],['Commercial',card.mvp_score],['Money',card.monetization_score]].map(([k,v])=><div className="rounded-xl bg-slate-950/80 p-2" key={k as string}><div className="text-slate-500">{labels[k as string]}</div><b>{v as any}</b></div>)}
  </div>

  {!compact&&business&&<section className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-4">
   <div className="mb-3 text-xs font-semibold tracking-wide text-blue-200">商业化判断 <span className="text-blue-300/60">Commercialization Brief</span></div>
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

  {!compact&&card.mvp_plan&&<div className="safe-text text-sm leading-6 text-slate-300"><div className="mb-1 text-xs font-semibold text-slate-500">MVP 计划</div>{card.mvp_plan}</div>}

  {card.risks?.length>0&&<div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3"><div className="mb-1 text-xs font-semibold text-amber-200">风险</div><ul className="list-disc pl-5 text-xs text-amber-100/90">{card.risks.map((r:string)=><li key={r}>{r}</li>)}</ul></div>}

  {!compact&&evidence.length>0&&<div><div className="mb-2 text-xs font-semibold tracking-wide text-slate-500">证据 Evidence</div><div className="space-y-1">{evidence.map((e:any,i:number)=><a key={i} className="block truncate text-xs text-blue-300 hover:text-blue-200" href={e.url} target="_blank">[{evidenceTypeLabel(e.type)}] {e.title}</a>)}</div></div>}

  {showFeedback&&<div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-3">
   <span className="text-xs text-slate-500">复核反馈会训练词根和屏蔽词</span>
   <Feedback id={card.id}/>
  </div>}
 </article>
}
