import {CreateProgressButton, ExportCardMarkdownButton, Feedback, ReanalyzeCardButton} from './Actions'
import {I18nText} from './I18nText'
import {ContextActions} from './ContextActions'
import {EvidenceTimeline} from './EvidenceTimeline'
import {ScoreHistory} from './ScoreHistory'

export function verdictClass(v:string){return v==='Adopted'?'badge badge-action':v==='Action'?'badge badge-action':v==='Watch'?'badge badge-watch':'badge badge-reject'}
export function verdictLabel(v:string){return v==='Adopted'?'已采纳 Adopted':v==='Action'?'行动 Action':v==='Watch'?'观察 Watch':v==='Reject'?'拒绝 Reject':v==='Block'?'屏蔽 Block':v}
function evidenceTypeLabel(t:string){const m:any={business:'商业判断',serp:'搜索结果',social:'社媒证据',competitor:'竞品',keyword:'关键词',source:'来源',url:'链接',error:'错误'}; return m[t]||t}
function shortText(s:string,n=180){s=(s||'').replace(/\s+/g,' ').trim(); return s.length>n?s.slice(0,n)+'…':s}

export function OpportunityCardView({card,compact=false,showFeedback=true,onFeedback,mode='review'}:{card:any;compact?:boolean;showFeedback?:boolean;onFeedback?:(label:string)=>void;mode?:'review'|'execute'}){
 const allEvidence=card.evidence_json||[]
 const business=allEvidence.find((e:any)=>e.type==='business') || {business_type:card.monetization_type, commercial_mvp:card.mvp_plan, verdict_reason:card.mvp_plan||'暂无完整商业分析；请先查看分数、风险和证据链，必要时重新生成商业分析。', missing_evidence:['缺少 business evidence block'], commercial_score:(Number(card.monetization_score||0)/100)||0, go_no_go:card.verdict==='Action'?'Go':card.verdict}
 const evidence=allEvidence.filter((e:any)=>e.type!=='business')
 const topEvidence=evidence.slice(0,2)
 const labels:any={Demand:'需求强度',SERP:'搜索缺口',Weakness:'竞品弱点',Commercial:'MVP 可行性',Money:'变现潜力'}
 return <article className="card safe-text space-y-4">
  <div className="space-y-3">
   <div className="min-w-0">
    <h2 className="text-lg font-semibold leading-7 text-white">{card.title}</h2>
    <p className="mt-1 text-sm leading-6 text-slate-400"><span className="text-slate-500">变现类型：</span>{business?.business_type||card.monetization_type||'未标注'}</p>
   </div>
   <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
    <span className={verdictClass(card.verdict)}>{verdictLabel(card.verdict)} · {card.score}</span>
    {business?.go_no_go&&<span className="badge badge-watch">商业判断：{business.go_no_go} · {Math.round((business.commercial_score||0)*100)}</span>}
    {business?.analysis_source&&<span className={String(business.analysis_source).startsWith('llm')?'badge badge-action':'badge badge-reject'}>{String(business.analysis_source).startsWith('llm')?'LLM 分析':'非 LLM / 模板分析'}：{business.analysis_source}</span>}
    {!compact&&<div className="ml-auto flex flex-wrap gap-2">{(card.feedback_label||card.verdict)==='Adopted'&&<CreateProgressButton id={card.id}/>}<ReanalyzeCardButton id={card.id}/><ExportCardMarkdownButton id={card.id}/></div>} 
   </div>
  </div>

  {showFeedback&&!compact&&mode==='review'&&<div className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-3">
   <div className="mb-2 text-xs font-semibold tracking-wide text-blue-200">复核决策</div>
   <div className="flex flex-wrap items-center justify-between gap-3">
    <span className="text-xs text-slate-400">改变机会状态：Adopted / Action / Watch / Reject / Block</span>
    {onFeedback?<InlineFeedback onFeedback={onFeedback}/>:<Feedback id={card.id}/>} 
   </div>
  </div>}

  <div className="grid grid-cols-2 gap-2 text-xs text-slate-300 sm:grid-cols-3 lg:grid-cols-5">
   {[['Demand',card.demand_score],['SERP',card.serp_gap_score],['Weakness',card.competitor_weakness_score],['Commercial',card.mvp_score],['Money',card.monetization_score]].map(([k,v])=><div className="rounded-xl bg-slate-950/80 p-2" key={k as string}><div className="text-slate-500">{labels[k as string]}</div><b>{v as any}</b></div>)}
  </div>

  {!compact&&<section className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
   <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
    <div><div className="text-xs font-semibold tracking-wide text-slate-500">证据与重评分</div><p className="mt-1 text-xs text-slate-400">证据保持客观；机会分数只在重评分事件里变化。</p></div>
    <ContextActions actions={[
     {label:'重新计算', actionType:'opportunity.rescore', targetType:'opportunity_card', targetId:card.id, variant:'secondary'},
     {label:'补证据', actionType:'opportunity.collect_evidence', targetType:'opportunity_card', targetId:card.id},
     ...((card.feedback_label||card.verdict)==='Adopted'?[]:[{label:'推送到机会推进' as const, actionType:'opportunity.push_progress', targetType:'opportunity_card', targetId:card.id, variant:'secondary' as const}]),
    ]}/>
   </div>
   <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
    <EvidenceTimeline targetType="opportunity_card" targetId={card.id}/>
    <ScoreHistory title="机会重评分历史" events={card.score_events||[]}/>
   </div>
  </section>}

  {card.opportunity_group&&<section className="rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-4">
   <div className="flex flex-wrap items-center justify-between gap-3">
    <div><div className="text-xs font-semibold tracking-wide text-cyan-200">相似机会组 / 证据链</div><p className="mt-1 text-sm text-slate-300">{card.opportunity_group.label} · 组概率 {Math.round((card.opportunity_group.probability||0)*100)}%</p></div>
    <div className="grid grid-cols-3 gap-2 text-center text-xs">
     <div className="rounded-xl bg-slate-950/70 px-3 py-2"><b className="text-white">{card.opportunity_group.variant_count}</b><div className="text-slate-500">变体</div></div>
     <div className="rounded-xl bg-slate-950/70 px-3 py-2"><b className="text-white">{card.opportunity_group.source_count}</b><div className="text-slate-500">来源</div></div>
     <div className="rounded-xl bg-slate-950/70 px-3 py-2"><b className="text-white">{card.opportunity_group.evidence_count}</b><div className="text-slate-500">证据</div></div>
    </div>
   </div>
   {!compact&&card.opportunity_group.variants?.length>0&&<div className="mt-3 flex flex-wrap gap-2">{card.opportunity_group.variants.slice(0,10).map((v:any)=><span key={`${v.type}-${v.id}`} className="rounded-full border border-slate-700 bg-slate-950/80 px-3 py-1 text-xs text-slate-300">{v.keyword} <span className="text-slate-500">· {v.source||'-'} · {v.status||'-'}</span></span>)}</div>}
  </section>}

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
   <div className="mb-3 flex items-center justify-between gap-2"><div className="text-xs font-semibold tracking-wide text-slate-500">决策摘要</div>{business.analysis_source&&<span className={String(business.analysis_source).startsWith('llm')?'badge badge-action':'badge badge-reject'}>{String(business.analysis_source).startsWith('llm')?'LLM':'非 LLM'}</span>}</div>
   {business.verdict_reason&&<div className="mb-3 rounded-xl border border-slate-800 bg-slate-900/70 p-3"><b className="text-sm text-slate-100">判断理由</b><p className="mt-1 text-sm leading-6 text-slate-300">{business.verdict_reason}</p></div>}
   {business.missing_evidence?.length>0&&<div className="mb-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100"><b>待补证据：</b>{business.missing_evidence.join('、')}</div>}
   <div className="grid gap-3 text-sm text-slate-300 md:grid-cols-2">
    <InfoBox title="目标用户" text={business.icp}/>
    <InfoBox title="付费触发" text={business.pay_trigger}/>
    <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 md:col-span-2"><b className="text-emerald-100">最小商业 MVP</b><p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-300">{business.commercial_mvp||card.mvp_plan||'-'}</p></div>
    <InfoBox title="收入路径" text={business.revenue_path||card.monetization_type}/>
    <InfoBox title="定价测试" text={business.pricing}/>
   </div>
  </section>}

  {card.risks?.length>0&&<div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3"><div className="mb-1 text-xs font-semibold text-amber-200">风险</div><ul className="list-disc pl-5 text-xs text-amber-100/90">{card.risks.slice(0,compact?2:4).map((r:string)=><li key={r}>{r}</li>)}</ul>{!compact&&card.risks.length>4&&<p className="mt-1 text-xs text-amber-100/70">另有 {card.risks.length-4} 条风险，见完整详情。</p>}</div>}

  {!compact&&topEvidence.length>0&&<div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3"><div className="mb-2 text-xs font-semibold tracking-wide text-slate-500">关键证据摘要</div><div className="space-y-1">{topEvidence.map((e:any,i:number)=><a key={i} className="block truncate text-xs text-blue-300 hover:text-blue-200" href={e.url} target="_blank">[{evidenceTypeLabel(e.type)}] {e.title}</a>)}</div></div>}

  {!compact&&card.collector_lineage&&<section className="rounded-2xl border border-purple-500/30 bg-purple-500/10 p-4">
   <div className="mb-3 text-xs font-semibold tracking-wide text-purple-200">采集来源链路 <span className="text-purple-300/60">Collector Lineage</span></div>
   <div className="grid gap-3 text-xs text-slate-300 md:grid-cols-2">
    <div><b className="text-slate-100">Collector</b><p className="mt-1 text-slate-400">{card.collector_lineage.candidate_source||card.keyword_source||'-'} {card.collector_lineage.candidate_id?`· candidate #${card.collector_lineage.candidate_id}`:''}</p></div>
    <div><b className="text-slate-100">Source</b><p className="mt-1 truncate text-slate-400">{card.collector_lineage.source_domain||'-'} {card.collector_lineage.source_url&&<a className="ml-1 text-blue-300 hover:text-blue-200" href={card.collector_lineage.source_url} target="_blank">打开</a>}</p></div>
   </div>
   {card.collector_lineage.collector_targets?.length>0&&<div className="mt-3 space-y-2">{card.collector_lineage.collector_targets.map((t:any)=><div key={t.id} className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-xs"><div className="flex flex-wrap items-center gap-2"><span className={t.type==='keyword'?'text-emerald-300':'text-blue-300'}>{t.type}</span><b className="text-slate-100">{t.value}</b><span className="text-slate-500">#{t.id}</span><span className="text-slate-500">priority {Math.round(t.priority||0)}</span><span className={t.status==='active'?'text-emerald-300':'text-amber-300'}>{t.status}</span></div><div className="mt-1 text-slate-500">success {t.success_count||0} · reject {t.reject_count||0}{t.topic?` · ${t.topic}`:''}</div></div>)}</div>}
  </section>}

  {!compact&&<details className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
   <summary className="cursor-pointer text-sm font-semibold text-slate-300 hover:text-white">展开完整分析</summary>
   <div className="mt-4 space-y-4">
    {business&&<section className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-4">
     <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h3 className="font-bold text-blue-100">1. 商业判断</h3><div className="flex flex-wrap gap-2 text-xs">{business.keyword_type&&<span className="badge">词类型：{business.keyword_type}</span>}{business.seo_fit&&<span className="badge badge-action">SEO：{business.seo_fit}</span>}{business.analysis_source&&<span className="badge badge-watch">{business.analysis_source}</span>}</div></div>
     {business.verdict_reason&&<p className="mb-3 rounded-xl bg-slate-950/60 p-3 text-sm leading-6 text-slate-200"><b>判断理由：</b>{business.verdict_reason}</p>}
     <div className="grid gap-3 text-sm md:grid-cols-2">
      <InfoBox title="目标用户" text={business.icp}/><InfoBox title="痛点" text={business.pain}/><InfoBox title="付费触发" text={business.pay_trigger}/><InfoBox title="切入点" text={business.wedge}/><InfoBox title="收入路径" text={business.revenue_path}/><InfoBox title="定价测试" text={business.pricing}/><InfoBox title="获客方式" text={business.gtm}/><InfoBox title="关键假设" text={business.key_assumption}/>
     </div>
    </section>}
    <section className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4">
     <h3 className="font-bold text-emerald-100">2. MVP / 第一笔钱测试</h3>
     <div className="mt-3 grid gap-3 md:grid-cols-2"><InfoBox title="最小商业 MVP" text={business?.commercial_mvp||card.mvp_plan}/><div className="rounded-xl bg-slate-950/70 p-3"><b className="text-slate-100">第一笔钱测试</b>{business?.first_sale_test?.length?<ol className="mt-2 list-decimal pl-5 text-sm text-slate-300">{business.first_sale_test.map((x:string)=><li key={x}>{x}</li>)}</ol>:<p className="mt-1 text-sm text-slate-400">暂无明确测试步骤。</p>}</div></div>
     {card.mvp_plan&&<div className="safe-text mt-3 rounded-xl bg-slate-950/70 p-3 text-sm leading-6 text-slate-300"><b className="text-slate-100">完整 MVP 计划：</b><br/>{card.mvp_plan}</div>}
    </section>
    <section className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4">
     <h3 className="font-bold text-amber-100">3. 风险与待补证据</h3>
     <div className="mt-3 grid gap-3 md:grid-cols-2"><ListBox title="风险" items={card.risks||[]}/><ListBox title="待补证据" items={business?.missing_evidence||[]}/></div>
    </section>
    <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
     <h3 className="font-bold text-slate-100">4. 证据链</h3>
     {evidence.length>0?<div className="mt-3 grid gap-2">{evidence.map((e:any,i:number)=>e.url?<a key={i} className="rounded-xl bg-slate-950 px-3 py-2 text-xs text-blue-300 hover:text-blue-200" href={e.url} target="_blank">[{evidenceTypeLabel(e.type)}] {e.title||e.url}</a>:<div key={i} className="rounded-xl bg-slate-950 px-3 py-2 text-xs text-slate-300">[{evidenceTypeLabel(e.type)}] {e.title||e.keyword||e.note||JSON.stringify(e).slice(0,160)}</div>)}</div>:<p className="mt-3 text-sm text-slate-500">暂无证据链。</p>}
    </section>
   </div>
  </details>}

  {showFeedback&&compact&&<div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-3">
   <span className="text-xs text-slate-500">复核反馈会训练词根和屏蔽词</span>
   {onFeedback?<InlineFeedback onFeedback={onFeedback}/>:<Feedback id={card.id}/>} 
  </div>}
 </article>
}

function InfoBox({title,text}:{title:string;text?:string}){return <div className="rounded-xl bg-slate-950/70 p-3"><b className="text-slate-100">{title}</b><p className="mt-1 text-sm leading-6 text-slate-400">{text||'-'}</p></div>}
function ListBox({title,items}:{title:string;items:string[]}){return <div className="rounded-xl bg-slate-950/70 p-3"><b className="text-slate-100">{title}</b>{items?.length?<ul className="mt-2 list-disc pl-5 text-sm text-slate-300">{items.map((x:string)=><li key={x}>{x}</li>)}</ul>:<p className="mt-1 text-sm text-slate-500">暂无。</p>}</div>}

function fbClass(x:string){const m:any={Watch:'border-blue-500/40 bg-blue-500/10 text-blue-200 hover:bg-blue-500/20',Action:'border-emerald-500/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20',Adopted:'border-purple-500/40 bg-purple-500/10 text-purple-200 hover:bg-purple-500/20',Reject:'border-amber-500/40 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20',Block:'border-rose-500/40 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20'}; return `rounded border px-2 py-1 text-xs ${m[x]}`}
function InlineFeedback({onFeedback}:{onFeedback:(label:string)=>void}){const labels:any={Adopted:'采纳',Action:'行动',Watch:'观察',Reject:'拒绝',Block:'屏蔽'}; return <div className="flex flex-wrap gap-2">{['Adopted','Action','Watch','Reject','Block'].map(x=><button key={x} title={x} className={fbClass(x)} onClick={()=>onFeedback(x)}>{labels[x]} <span className="opacity-60">{x}</span></button>)}</div>}
