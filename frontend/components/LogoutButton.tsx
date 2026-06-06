'use client'
export function LogoutButton(){return <button className="mt-4 w-full rounded-xl border border-slate-700 px-3 py-2 text-left text-sm text-slate-400 hover:bg-slate-800 hover:text-slate-100" onClick={()=>{localStorage.removeItem('dh_token'); document.cookie='dh_token=; path=/; max-age=0'; location.href='/login'}}>Logout</button>}
