'use client'

type ScoreEvent = {
  id?: number
  created_at?: string
  event_type?: string
  reason?: string
  old_score?: number
  new_score?: number
  delta?: number
}

type Props = {
  title?: string
  events?: ScoreEvent[]
}

function fmt(value?: string) {
  if (!value) return '暂无时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'})
}

export function ScoreHistory({title = '评分历史', events = []}: Props) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
      <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
      {events.length ? (
        <div className="mt-3 space-y-2">
          {events.map((event, index) => (
            <div key={event.id ?? index} className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-2 text-sm">
              <span className="text-slate-300">{event.reason || event.event_type || '重新计算'}</span>
              <span className="text-slate-500">{fmt(event.created_at)}</span>
              <span className="font-mono text-blue-200">{event.old_score ?? '-'} → {event.new_score ?? '-'}</span>
            </div>
          ))}
        </div>
      ) : <p className="mt-3 text-sm text-slate-400">暂无评分事件。</p>}
    </section>
  )
}
