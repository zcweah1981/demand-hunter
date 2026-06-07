'use client'
import {useEffect, useState} from 'react'

export type Lang='zh'|'en'
const dict:Record<string,Record<Lang,string>>={
 autopilot:{zh:'自动猎手',en:'Autopilot'}, overview:{zh:'概览',en:'Overview'}, discovery:{zh:'四找发现',en:'Discovery'}, dashboard:{zh:'仪表盘',en:'Dashboard'}, review:{zh:'复核',en:'Review'}, cards:{zh:'机会',en:'Opportunities'}, keywords:{zh:'关键词',en:'Keywords'}, roots:{zh:'词根库',en:'Root Library'}, runs:{zh:'运行历史',en:'Run History'}, settings:{zh:'设置',en:'Settings'}, advanced:{zh:'高级',en:'Advanced'},
 qualityFormula:{zh:'质量公式',en:'Quality Formula'}, formula:{zh:'需求 × 入口 × 缺口 × MVP × 变现',en:'Demand × Entry × Gap × MVP × Monetization'},
 configuration:{zh:'配置',en:'Configuration'}, saveGroup:{zh:'保存模块',en:'Save module'}, testProviders:{zh:'测试搜索源',en:'Test Providers'}, providerHealth:{zh:'Provider 健康检查',en:'Provider Health'}, testing:{zh:'测试中...',en:'Testing...'},
 searchProviders:{zh:'搜索总控',en:'Search Control'}, searchDesc:{zh:'Provider 顺序、重试和 SERP 策略总控',en:'Provider order, retry, and SERP strategy control'},
 searxngDesc:{zh:'SearXNG 地址池轮询、fallback URL、引擎和访问令牌',en:'SearXNG URL pool rotation, fallback URL, engines, and access token'}, braveDesc:{zh:'Brave 多 Key 轮询',en:'Brave multi-key rotation'}, tavilyDesc:{zh:'Tavily 多 Key 轮询',en:'Tavily multi-key rotation'},
 llmDesc:{zh:'Primary + fallback 模型配置',en:'Primary + fallback model configuration'}, automation:{zh:'自动化',en:'Automation'}, automationDesc:{zh:'自动运行和 Four-Find 闭环策略',en:'Auto run and Four-Find loop policy'}, quality:{zh:'质量',en:'Quality'}, qualityDesc:{zh:'Action 门槛和噪音控制',en:'Action threshold and noise controls'}, security:{zh:'安全',en:'Security'}, securityDesc:{zh:'登录密码修改',en:'Login password change'},
 secret:{zh:'密钥',en:'secret'}, rotation:{zh:'轮询',en:'rotation'}, noEntries:{zh:'暂无明细',en:'No entries yet'}, confirmAdd:{zh:'确认新增',en:'Confirm add'}, remove:{zh:'删除',en:'Remove'}, pasteBulk:{zh:'也可直接批量粘贴，每行一条',en:'Bulk paste is also supported, one per line'},
 rotationHint:{zh:'支持多条，按顺序轮询；某条失败自动尝试下一条。',en:'Supports multiple entries. Rotates in order; failed entries fall through to the next.'},
 fallbackHint:{zh:'JSON 数组：provider/model/api_key。Primary 失败后按顺序 fallback。',en:'JSON array: provider/model/api_key. Fallbacks run in order after primary fails.'},
 changePassword:{zh:'修改登录密码',en:'Change login password'}, currentPassword:{zh:'当前密码',en:'Current password'}, newPassword:{zh:'新密码（至少 8 位）',en:'New password (min 8 chars)'}, updatePassword:{zh:'更新密码',en:'Update password'},
 saved:{zh:'已保存',en:'Saved'}, passwordChanged:{zh:'密码已修改',en:'Password changed'}, searchOk:{zh:'搜索正常',en:'Search OK'},

 settingsTitle:{zh:'设置',en:'Settings'}, settingsSubtitle:{zh:'分组配置中心：搜索源、模型、自动任务、质量门槛和安全设置。',en:'Grouped configuration center: search providers, models, automation, quality gates, and security.'},
 settingsMenu:{zh:'设置',en:'Settings'}, notSaved:{zh:'尚未保存',en:'Not saved yet'}, plain:{zh:'普通',en:'plain'},
 changingPassword:{zh:'正在修改密码...',en:'Changing password...'}, searchFailed:{zh:'搜索失败',en:'Search failed'}, pasteNewApiKey:{zh:'粘贴新的 API Key',en:'Paste new API key'}, provider:{zh:'提供商',en:'Provider'}, model:{zh:'模型',en:'Model'}, addFallback:{zh:'新增 fallback',en:'Add fallback'}, clearAll:{zh:'清空全部',en:'Clear all'}, configured:{zh:'已配置',en:'configured'}, unsaved:{zh:'有未保存修改',en:'Unsaved changes'}, saving:{zh:'保存中...',en:'Saving...'}, savedState:{zh:'已保存',en:'Saved'}, clearAllConfirm:{zh:'确认清空全部已配置密钥？',en:'Clear all configured keys?'}, clearFallbackConfirm:{zh:'确认清空全部 fallback 模型？',en:'Clear all fallback models?'},
 loginTitle:{zh:'Demand Hunter 登录',en:'Demand Hunter Login'}, loginSubtitle:{zh:'上线系统已启用访问保护。',en:'Access protection is enabled for this system.'}, loginButton:{zh:'登录',en:'Login'}, loggingIn:{zh:'登录中...',en:'Logging in...'}, password:{zh:'密码',en:'Password'},
}

export function tr(key:string, lang:Lang){return dict[key]?.[lang] || key}
export function useLang(){
 const [lang,setLangState]=useState<Lang>('zh')
 useEffect(()=>{const v=localStorage.getItem('dh_lang'); if(v==='en'||v==='zh') setLangState(v)},[])
 function setLang(v:Lang){localStorage.setItem('dh_lang',v); setLangState(v)}
 return {lang,setLang,t:(key:string)=>tr(key,lang)}
}
