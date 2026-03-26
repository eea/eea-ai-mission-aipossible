import { useEffect, useState } from 'react'
import { getHealth, getUseCases, runAnalysis, runAnalysisWithPrompt } from './api/client'
import { HealthBadge } from './components/HealthBadge'
import { RunForm } from './components/RunForm'
import { RunResult } from './components/RunResult'
import type { AnalysisRunResponse } from './types'

type HealthStatus = 'loading' | 'ok' | 'error'

export default function App() {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('loading')
  const [useCases, setUseCases] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisRunResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getHealth()
      .then(() => setHealthStatus('ok'))
      .catch(() => setHealthStatus('error'))
    getUseCases()
      .then(setUseCases)
      .catch(() => {})
  }, [])

  const handleSubmit = async (
    useCase: string,
    maxItems: number | undefined,
    promptFile: File | undefined,
  ) => {
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const res = promptFile
        ? await runAnalysisWithPrompt(useCase, promptFile, maxItems)
        : await runAnalysis(useCase, maxItems)
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header
        className="px-6 py-5 flex items-center justify-between"
        style={{ background: 'linear-gradient(135deg, #0f3362 0%, #1a4e8a 60%, #2563c4 100%)' }}
      >
        <div className="flex items-center gap-3">
          <img
            src="/logo.png"
            alt="Mission AIpossible logo"
            className="h-12 w-12 rounded-xl object-contain bg-white/10 p-1 shadow-md"
          />
          <div>
            <h1 className="text-white font-bold text-lg leading-tight">Mission AIpossible</h1>
            <p className="text-blue-200 text-xs mt-0.5">Climate Adaptation Analysis</p>
          </div>
        </div>
        <HealthBadge status={healthStatus} />
      </header>

      {/* Main */}
      <main className="flex-1 flex flex-col items-center px-4 py-10">
        <div className="w-full max-w-lg space-y-5">

          {/* Form card */}
          <div className="rounded-2xl bg-white shadow-card-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
              <span className="text-brand-orange text-base">⚡</span>
              <h2 className="text-sm font-semibold text-gray-700">Run Analysis</h2>
            </div>
            <div className="p-6">
              {healthStatus === 'error' ? (
                <p className="text-sm text-red-500 text-center py-4">
                  Cannot reach API. Make sure the server is running on port 8000.
                </p>
              ) : useCases.length === 0 && healthStatus === 'ok' ? (
                <p className="text-sm text-amber-600 text-center py-4">
                  No use cases found. Check your <code className="bg-amber-50 px-1 rounded">config/analysis_use_cases.json</code>.
                </p>
              ) : (
                <RunForm useCases={useCases} loading={loading} onSubmit={handleSubmit} />
              )}
            </div>
          </div>

          {/* Error banner */}
          {error && (
            <div className="animate-fade-in rounded-xl border border-red-200 bg-red-50 px-4 py-3 flex items-start gap-3 shadow-sm">
              <span className="text-red-400 text-base mt-0.5">✗</span>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Result card */}
          {result && <RunResult result={result} />}
        </div>
      </main>

      {/* Footer */}
      <footer className="text-center text-xs text-gray-300 py-6">
        European Environment Agency · Mission AIpossible
      </footer>
    </div>
  )
}
