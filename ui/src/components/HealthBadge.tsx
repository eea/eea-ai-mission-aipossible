type Status = 'loading' | 'ok' | 'error'

const CONFIG: Record<Status, { dot: string; text: string; label: string }> = {
  loading: { dot: 'bg-amber-400 animate-pulse', text: 'text-blue-200', label: 'Connecting…' },
  ok:      { dot: 'bg-emerald-400',             text: 'text-blue-200', label: 'API online'  },
  error:   { dot: 'bg-red-400',                 text: 'text-red-300',  label: 'API offline' },
}

export function HealthBadge({ status }: { status: Status }) {
  const { dot, text, label } = CONFIG[status]
  return (
    <span className={`flex items-center gap-2 text-xs font-medium ${text}`}>
      <span className={`inline-block h-2 w-2 rounded-full ${dot}`} />
      {label}
    </span>
  )
}
