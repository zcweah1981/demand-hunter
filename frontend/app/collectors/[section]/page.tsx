import {CollectorsPage} from '../../../components/CollectorsPage'

export default async function Page({params}:{params:Promise<{section:string}>}){
 const {section='overview'}=await params
 return <CollectorsPage initialSection={section}/>
}
