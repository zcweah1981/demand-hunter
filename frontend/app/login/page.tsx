'use client'
import {useState} from 'react'
export default function Login(){
 const [password,setPassword]=useState(''); const [err,setErr]=useState(''); const [loading,setLoading]=useState(false)
 async function submit(e:React.FormEvent){e.preventDefault(); setLoading(true); setErr('')
  const res=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password})})
  if(!res.ok){setErr('密码错误或服务未就绪'); setLoading(false); return}
  const data=await res.json(); localStorage.setItem('dh_token', data.token); document.cookie=`dh_token=${data.token}; path=/; max-age=2592000; SameSite=Lax`; location.href='/'
 }
 return <div className="flex min-h-screen w-full items-center justify-center bg-slate-950"><form onSubmit={submit} className="card w-full max-w-md space-y-4"><h1 className="text-2xl font-bold">Demand Hunter 登录</h1><p className="text-sm text-slate-400">上线系统已启用访问保护。</p><input className="input w-full" type="password" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} autoFocus />{err&&<p className="text-sm text-red-400">{err}</p>}<button className="btn w-full" disabled={loading}>{loading?'登录中...':'登录'}</button></form></div>
}
