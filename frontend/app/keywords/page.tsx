import {api, Keyword} from '../../lib/api'
import {KeywordLibraryPage} from '../../components/KeywordLibraryPage'

export default async function Page() {
  const rows = await api<Keyword[]>('/api/keywords')
  return <KeywordLibraryPage rows={rows} />
}
