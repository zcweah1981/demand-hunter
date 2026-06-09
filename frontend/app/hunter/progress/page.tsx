import {api} from '../../../lib/api'
import {ProgressPage} from '../../../components/ProgressPage'

export default async function Page(){
 const [projects, adopted] = await Promise.all([
  api<any[]>('/api/progress').catch(()=>[]),
  api<any[]>('/api/cards/groups?verdict=Adopted').catch(()=>[]),
 ])
 return <ProgressPage initialProjects={projects} adoptedCards={adopted}/>
}
