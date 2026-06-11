const browserApi = process.env.NEXT_PUBLIC_API_URL || ''
const serverApi = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8100'
export const API = typeof window === 'undefined' ? serverApi : browserApi

export function authToken(){
  if (typeof window === 'undefined') return process.env.INTERNAL_API_TOKEN || ''
  return localStorage.getItem('dh_token') || ''
}

export async function api<T>(path:string, init?:RequestInit):Promise<T>{
  const headers:any = {'Content-Type':'application/json', ...(init?.headers||{})}
  const token = authToken()
  if(token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${API}${path}`, { ...init, cache:'no-store', headers })
  if(res.status === 401 && typeof window !== 'undefined'){
    localStorage.removeItem('dh_token')
    if(!location.pathname.startsWith('/login')) location.href='/login'
  }
  if(!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json()
}
export type Keyword={id:number;query:string;source:string;intent:string;status:string;score:number;root_terms:string[];created_at:string}
export type Card={id:number;keyword_id:number;title:string;verdict:string;score:number;demand_score:number;serp_gap_score:number;competitor_weakness_score:number;mvp_score:number;monetization_score:number;monetization_type:string;mvp_plan:string;evidence_json:any[];risks:string[];feedback_label:string;source_keyword?:string;keyword_source?:string;keyword_intent?:string}
export type CandidateEntry={id:number;entry_type:string;name:string;source:string;source_role:string;source_url:string;status:string;priority:number;trend_score:number;demand_score:number;quality_score:number;raw_context?:Record<string,unknown>;next_action?:string;next_due_at?:string|null;created_at:string;updated_at?:string}
export type EvidenceItem={id:number;source_type:string;source_name:string;url:string;title:string;summary:string;raw_excerpt:string;confidence:number;captured_at:string;created_at?:string}
export type EvidenceLink={id:number;evidence_id:number;target_type:string;target_id:string;relation_type:string;relation_reason:string;created_by:string;created_at:string}
export type EvidenceTimelineItem={evidence:EvidenceItem|null;link:EvidenceLink}
export type AutomationDueAction={kind:string;target_type:string;target_id:string|number;action:string;due_at?:string|null;reason?:string}
export type ActionRequest={id:number;action_type:string;target_type:string;target_id:string;requested_by:string;reason:string;status:string;confirm:boolean;result_json?:unknown;created_at:string;executed_at?:string|null}

const json = (body:unknown) => ({method:'POST', body:JSON.stringify(body)})

export const discoveryApi = {
  entries: (params = '') => api<CandidateEntry[]>(`/api/entries${params}`),
  entry: (id:number|string) => api<CandidateEntry>(`/api/entries/${id}`),
  pushEntry: (id:number|string) => api<{entry:CandidateEntry; action:string}>(`/api/entries/${id}/push`, {method:'POST'}),
}

export const evidenceApi = {
  list: (params = '') => api<EvidenceItem[]>(`/api/evidence${params}`),
  timeline: (targetType:string, targetId:string|number) => api<EvidenceTimelineItem[]>(`/api/evidence/targets/${targetType}/${targetId}/timeline`),
  derived: () => api<CandidateEntry[]>('/api/evidence/derived'),
  link: (evidenceId:number|string, payload:{target_type:string; target_id:string; relation_type:string; relation_reason?:string; created_by?:string}) => api<EvidenceLink>(`/api/evidence/${evidenceId}/links`, json(payload)),
}

export const automationCycleApi = {
  due: () => api<AutomationDueAction[]>('/api/automation-cycle/due'),
  run: (payload:Record<string,unknown> = {}) => api<Record<string,unknown>>('/api/automation-cycle/run', json(payload)),
  runs: () => api<any[]>('/api/automation-cycle/runs'),
}

export const actionsApi = {
  list: (params = '') => api<ActionRequest[]>(`/api/actions${params}`),
  create: (payload:{action_type:string; target_type:string; target_id:string; requested_by?:string; reason?:string; confirm?:boolean}) => api<ActionRequest>('/api/actions', json(payload)),
  execute: (id:number|string, confirm = false) => api<Record<string,unknown>>(`/api/actions/${id}/execute`, json({confirm})),
}
