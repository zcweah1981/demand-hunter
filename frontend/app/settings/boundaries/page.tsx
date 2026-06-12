import {api} from '../../../lib/api'
import {SettingsForm} from '../../../components/SettingsForm'
import {SettingsHeader} from '../../../components/SettingsHeader'

export const dynamic = 'force-dynamic'

export default async function Page() {
  const rows = await api<any[]>('/api/settings')
  return <div className="space-y-6"><SettingsHeader group="boundaries"/><SettingsForm rows={rows} initialGroup="boundaries"/></div>
}
