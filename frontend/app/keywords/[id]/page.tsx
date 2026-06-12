import {api} from '../../../lib/api'
import {KeywordDetailContent} from '../../../components/KeywordDetailContent'

export default async function Page({params}: {params: Promise<{id: string}>}) {
  const {id} = await params
  const data = await api<any>(`/api/keywords/${id}`)
  return <KeywordDetailContent data={data} />
}
