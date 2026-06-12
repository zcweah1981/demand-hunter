import {CluePoolPage} from '../../../components/CluePoolPage'
import {discoveryApi} from '../../../lib/api'

export const dynamic = 'force-dynamic'

export default async function Page() {
  const data = await discoveryApi.clues('?limit=200').catch(() => ({items: [], totals: {}, count: 0}))

  return <CluePoolPage data={data} />
}
