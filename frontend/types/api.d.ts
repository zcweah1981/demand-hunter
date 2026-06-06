export type ApiSetting = {key:string; value:string; secret:boolean; updated_at?:string}
export type ApiKeyword = {id:number; query:string; source:string; intent:string; status:string; score:number; root_terms:string[]; created_at:string}
export type ApiCard = {id:number; keyword_id:number; title:string; verdict:string; score:number; demand_score:number; serp_gap_score:number; competitor_weakness_score:number; mvp_score:number; monetization_score:number; monetization_type:string; mvp_plan:string; evidence_json:any[]; risks:string[]; feedback_label:string; feedback_note?:string; created_at?:string}
export type ApiRun = {id:number; kind:string; status:string; summary:any; started_at:string; finished_at?:string|null}
export type DiscoveryJob<T=any> = {id?:string; job_id?:string; status:'pending'|'running'|'ok'|'failed'; poll?:string; result?:T; error?:string|null}
export type DiscoveryLoopStatus = {funnel:Record<string,number>; expansion_status:Record<string,number>; competitor_keyword_status:Record<string,number>; card_verdicts:Record<string,number>; card_feedback:Record<string,number>; keyword_sources:Record<string,number>; seed_scores:any[]; top_competitor_domains:any[]}
