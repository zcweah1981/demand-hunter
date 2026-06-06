'use client'

export async function pollJob<T=any>(apiFn: (path:string, init?:RequestInit)=>Promise<any>, submitPath: string, submitBody: any, opts?:{interval?:number; maxWait?:number}): Promise<T> {
  const interval = opts?.interval || 2000
  const maxWait = opts?.maxWait || 120000
  const submitRes: any = await apiFn(submitPath, {method:'POST', body:JSON.stringify(submitBody)})
  if (submitRes.status === 'ok' && submitRes.result) return submitRes.result as T
  const jobId = submitRes.job_id
  if (!jobId) throw new Error('No job_id returned')
  const pollPath = submitRes.poll || `/api/discovery/job/${jobId}`
  const start = Date.now()
  while (Date.now() - start < maxWait) {
    await new Promise(r => setTimeout(r, interval))
    const job: any = await apiFn(pollPath)
    if (job.status === 'ok' && job.result !== undefined) return job.result as T
    if (job.status === 'failed') throw new Error(job.error || 'Job failed')
  }
  throw new Error('Job timed out')
}
