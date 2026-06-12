'use client'
import {useLang} from '../lib/i18n'
const names:any={'api-keys':'API Key 管理中心',search:'searchProviders',searxng:'SearXNG',brave:'Brave',tavily:'Tavily',llm:'LLM',automation:'automation','automation-cycle':'自动运行周期','source-budget':'来源预算',boundaries:'边界与偏好',quality:'quality',security:'security'}
export function SettingsHeader({group}:{group:string}){const {t}=useLang(); const name=names[group]; return <div><h1 className="text-3xl font-bold">{t('settingsTitle')} / {name? (name==='SearXNG'||name==='Brave'||name==='Tavily'||name==='LLM'||name==='API Key 管理中心'?name:t(name)) : group}</h1><p className="mt-2 text-slate-400">{t('settingsSubtitle')}</p></div>}
