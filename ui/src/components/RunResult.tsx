import { downloadUrl } from '../api/client'
import type { AnalysisRunResponse } from '../types'

function triggerDownload(url: string) {
  const a = document.createElement('a')
  a.href = url
  a.click()
}

function StatCard({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm text-center">
      <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">{label}</div>
      <div className={`text-lg font-bold ${accent ?? 'text-gray-800'}`}>{value}</div>
    </div>
  )
}

export function RunResult({ result }: { result: AnalysisRunResponse }) {
  return (
    <div className="animate-fade-in rounded-2xl border border-emerald-100 bg-white shadow-card overflow-hidden">
      {/* Header strip */}
      <div className="bg-gradient-to-r from-brand-green to-emerald-500 px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-white font-semibold text-sm">
          <span className="text-lg">✓</span> Run complete
        </div>
        <code className="text-xs text-white/70 font-mono bg-black/20 rounded px-2 py-0.5">
          {result.run_id}
        </code>
      </div>

      <div className="p-5 space-y-5">
        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Processed" value={result.processed} accent="text-brand-blue" />
          <StatCard label="Skipped"   value={result.skipped} />
          <StatCard label="Elapsed"   value={`${result.total_elapsed_minutes.toFixed(1)} min`} />
          <StatCard label="Model"     value={result.model} accent="text-brand-orange" />
        </div>

        {/* Provider pill */}
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 font-medium text-gray-500">
            {result.provider}
          </span>
          <span className="text-gray-300">·</span>
          <span>{result.processed} item{result.processed !== 1 ? 's' : ''} written to</span>
          <code className="truncate max-w-[180px] text-gray-500">{result.run_id}</code>
        </div>

        {/* Warnings */}
        {result.warnings.length > 0 && (
          <ul className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 space-y-1">
            {result.warnings.map((w, i) => (
              <li key={i} className="text-xs text-amber-700">⚠ {w}</li>
            ))}
          </ul>
        )}

        {/* Download buttons */}
        <div className="flex gap-3 pt-1">
          <button
            onClick={() => triggerDownload(downloadUrl('excel', result.run_id))}
            className="btn-outline flex-1 border-brand-green/40 text-brand-green hover:border-brand-green justify-center"
          >
            <span>📊</span> Download Excel
          </button>
          <button
            onClick={() => triggerDownload(downloadUrl('zip', result.run_id))}
            className="btn-outline border-brand-blue/30 text-brand-blue hover:border-brand-blue justify-center"
            style={{ flex: '0 0 auto' }}
          >
            <span>📦</span> ZIP
          </button>
        </div>
      </div>
    </div>
  )
}
