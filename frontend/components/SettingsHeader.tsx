'use client'
import {useLang} from '../lib/i18n'
const names:any={search:'searchProviders',searxng:'SearXNG',brave:'Brave',tavily:'Tavily',llm:'LLM',automation:'automation',quality:'quality',security:'security'}
export function SettingsHeader({group}:{group:string}){const {t}=useLang(); const name=names[group]; return <div><h1 className="text-3xl font-bold">{t('settingsTitle')} / {name? (name==='SearXNG'||name==='Brave'||name==='Tavily'||name==='LLM'?name:t(name)) : group}</h1><p className="mt-2 text-slate-400">{t('settingsSubtitle')}</p></div>}
