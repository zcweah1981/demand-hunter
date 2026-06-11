import {evidenceApi, EvidenceTimelineItem} from '../lib/api'

type Props = {
  targetType: string
  targetId: string | number
}

function fmtTime(value?: string) {
  if (!value) return '时间未知'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'})
}

function relationLabel(raw: string) {
  const map: Record<string, string> = {support: '支持关系', weaken: '削弱关系', neutral: '背景关系'}
  return map[raw] || raw || '未标注关系'
}

export async function EvidenceTimeline({targetType, targetId}: Props) {
  const rows = await evidenceApi.timeline(targetType, targetId).catch(() => [] as EvidenceTimelineItem[])

  if (!rows.length) {
    return <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-400">暂无关联证据。</div>
  }

  return (
    <div className="space-y-3">
      {rows.map((item, index) => (
        <div key={`${item.link.id}-${index}`} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="badge">{relationLabel(item.link.relation_type)}</span>
            <span className="text-xs text-slate-500">{fmtTime(item.evidence?.captured_at || item.link.created_at)}</span>
          </div>
          <h3 className="mt-3 text-sm font-semibold text-slate-100">{item.evidence?.title || item.evidence?.source_name || '未命名证据'}</h3>
          {item.evidence?.summary && <p className="mt-2 text-sm text-slate-300">{item.evidence.summary}</p>}
          {item.link.relation_reason && <p className="mt-2 text-xs text-blue-200">服务关系：{item.link.relation_reason}</p>}
          {item.evidence?.url && <a className="mt-2 block truncate text-xs text-blue-300 hover:text-blue-200" href={item.evidence.url} target="_blank" rel="noreferrer">{item.evidence.url}</a>}
        </div>
      ))}
    </div>
  )
}
