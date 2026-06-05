'use client'
import {useEffect, useState} from 'react'
import {api} from '../lib/api'

export function AuthGate({children}:{children:React.ReactNode}){
  const [ready,setReady]=useState(false)
  useEffect(()=>{
    if(location.pathname.startsWith('/login')){setReady(true);return}
    api('/api/auth/me').then(()=>setReady(true)).catch(()=>{location.href='/login'})
  },[])
  if(!ready) return <div className="p-8 text-slate-400">Checking login...</div>
  return <>{children}</>
}
