import {redirect} from 'next/navigation'
export default async function Page({searchParams}:{searchParams?:Promise<Record<string,string|string[]|undefined>>}){
 const params=(await (searchParams||Promise.resolve({}))) as Record<string,string|string[]|undefined>
 const verdict=Array.isArray(params.verdict)?params.verdict[0]:params.verdict
 redirect(`/hunter/opportunities${verdict?`?verdict=${verdict}`:''}`)
}
