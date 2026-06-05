const browserApi = process.env.NEXT_PUBLIC_API_URL || ''
const serverApi = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8100'
export const API = typeof window === 'undefined' ? serverApi : browserApi
export async function api<T>(path:string, init?:RequestInit):Promise<T>{
  const res = await fetch(`${API}${path}`, { ...init, cache:'no-store', headers:{'Content-Type':'application/json', ...(init?.headers||{})} })
  if(!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json()
}
export type Keyword={id:number;query:string;source:string;intent:string;status:string;score:number;root_terms:string[];created_at:string}
export type Card={id:number;keyword_id:number;title:string;verdict:string;score:number;demand_score:number;serp_gap_score:number;competitor_weakness_score:number;mvp_score:number;monetization_score:number;monetization_type:string;mvp_plan:string;evidence_json:any[];risks:string[];feedback_label:string}
