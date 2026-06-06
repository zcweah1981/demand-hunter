export function StatCard({label,value,hint,tone='slate'}:{label:string;value:any;hint?:string;tone?:'slate'|'green'|'amber'|'rose'|'blue'}){
 const tones:any={slate:'from-slate-800 to-slate-900',green:'from-emerald-900/70 to-slate-900',amber:'from-amber-900/70 to-slate-900',rose:'from-rose-900/70 to-slate-900',blue:'from-blue-900/70 to-slate-900'}
 return <div className={`rounded-2xl border border-slate-700 bg-gradient-to-br ${tones[tone]} p-5 shadow`}><div className="kpi-label">{label}</div><div className="mt-2 text-3xl font-bold text-white">{value}</div>{hint&&<div className="mt-1 text-xs text-slate-400">{hint}</div>}</div>
}
