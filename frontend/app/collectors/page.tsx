const collectors = [
 {id:'suggest',name:'搜索联想 / 相关搜索',tag:'词找词',status:'待接入',desc:'从 Google/Bing/SearXNG suggest、related searches、PAA 中扩展长尾搜索词。',feeds:['Google Suggest','Related Search','People Also Ask','SearchSuggest.tips'],output:'candidate_keyword → Four-Find → SEO 验证'},
 {id:'trends',name:'趋势词 / 新词',tag:'新词发现',status:'待接入',desc:'从 Google Trends、rising queries、AI suggested terms 中发现上升词和新词。',feeds:['Google Trends','pytrends','Exploding Topics','Glimpse'],output:'rising keyword + country/trend → Four-Find → SEO 验证'},
 {id:'sitemap',name:'Sitemap 监控',tag:'站找词',status:'优先开发',desc:'监控竞品 sitemap 新增 URL，从路径和标题抽取新页面、新工具、新长尾词。',feeds:['robots.txt','sitemap.xml','competitor domains'],output:'new URL/page → keyword extraction → Four-Find → SEO 验证'},
 {id:'similarweb',name:'SimilarWeb 采集',tag:'站找词 / 站找站',status:'需 API',desc:'获取站点关键词、相似站、出站流量、着陆页新点击量，发现正在涨的页面和产品。',feeds:['SimilarWeb keywords','Similar sites','Outgoing traffic','Landing pages'],output:'site/page/keyword → Four-Find → SEO 验证'},
 {id:'extensions',name:'插件差评挖掘',tag:'抱怨找需求',status:'独立模块',desc:'找高下载、低评分、差评多的浏览器插件，从用户抱怨抽取具体需求词。',feeds:['Chrome Web Store','Firefox Add-ons','Edge Add-ons'],output:'complaint topic → candidate keyword → SEO 验证'},
 {id:'requests',name:'AI 工具请求',tag:'请求找需求',status:'独立模块',desc:'抓取 AI 工具请求/愿望单，按最新、投票数、重复诉求提取候选词。',feeds:['TheresAnAIForThat Requests','ProductHunt discussions','AI directories'],output:'request text → keyword → Four-Find → SEO 验证'},
 {id:'source-radar',name:'一手信息源雷达',tag:'信息溯源',status:'独立模块',desc:'监控 Hugging Face、arXiv、GitHub、HN、X 早期发布者，捕捉新模型/新技术/新词。',feeds:['Hugging Face','arXiv','GitHub Trending','Hacker News','X accounts'],output:'early signal → new keyword → Trends/SERP/SEO 验证'},
]

export default function Page(){
 return <div className="space-y-6">
  <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-blue-950/60 via-slate-950 to-slate-950 p-7 shadow-2xl">
   <p className="text-sm font-semibold uppercase tracking-[0.3em] text-blue-300">Collectors</p>
   <h1 className="mt-3 text-4xl font-black text-white">采集器</h1>
   <p className="mt-3 max-w-3xl text-slate-300">统一管理所有找词/找站/找证据入口。采集器只负责发现候选，不能直接产出机会；所有候选最终都进入 Four-Find 扩展和 SEO 验证。</p>
  </section>

  <section className="panel">
   <h2 className="text-xl font-bold">统一流转</h2>
   <div className="mt-4 grid gap-3 md:grid-cols-5">
    {['采集源','候选池','Four-Find 扩展','SEO 验证','机会卡'].map((x,i)=><div key={x} className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-center"><div className="text-xs text-slate-500">Step {i+1}</div><b className="text-slate-100">{x}</b></div>)}
   </div>
   <p className="mt-4 text-sm text-slate-400">原则：所有入口都可以找词，但所有词都必须过 SEO。Discovery 负责发现，Four-Find 负责扩展，SEO 负责定生死，LLM 负责解释和成卡。</p>
  </section>

  <section className="grid gap-4 xl:grid-cols-2">
   {collectors.map(c=><article key={c.id} id={c.id} className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl">
    <div className="flex flex-wrap items-start justify-between gap-3">
     <div><div className="text-xs uppercase tracking-[0.25em] text-blue-300">{c.tag}</div><h2 className="mt-2 text-xl font-bold text-white">{c.name}</h2></div>
     <span className={c.status==='优先开发'?'badge badge-action':c.status==='需 API'?'badge badge-watch':'badge'}>{c.status}</span>
    </div>
    <p className="mt-3 text-sm leading-6 text-slate-300">{c.desc}</p>
    <div className="mt-4"><div className="mb-2 text-xs font-semibold text-slate-500">数据源</div><div className="flex flex-wrap gap-2">{c.feeds.map(f=><span key={f} className="rounded-lg bg-slate-900 px-2 py-1 text-xs text-slate-300">{f}</span>)}</div></div>
    <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/50 p-3 text-xs text-slate-400"><b className="text-slate-300">输出：</b>{c.output}</div>
   </article>)}
  </section>
 </div>
}
