import type { AnalysisRunResponse, HealthResponse } from '../types'

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((err as { detail?: string }).detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function getHealth(): Promise<HealthResponse> {
  return handleResponse(await fetch('/health'))
}

export async function getUseCases(): Promise<string[]> {
  return handleResponse(await fetch('/v1/analysis/use-cases'))
}

export async function runAnalysis(
  useCase: string,
  maxItems: number | undefined,
): Promise<AnalysisRunResponse> {
  return handleResponse(
    await fetch('/v1/analysis/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ use_case: useCase, max_items: maxItems ?? null }),
    }),
  )
}

export async function runAnalysisWithPrompt(
  useCase: string,
  promptFile: File,
  maxItems: number | undefined,
): Promise<AnalysisRunResponse> {
  const form = new FormData()
  form.append('use_case', useCase)
  form.append('prompt_file', promptFile)
  if (maxItems != null) form.append('max_items', String(maxItems))
  return handleResponse(
    await fetch('/v1/analysis/runs/upload-prompt', { method: 'POST', body: form }),
  )
}

export function downloadUrl(type: 'zip' | 'excel', runId: string): string {
  return type === 'zip'
    ? `/v1/analysis/runs/${runId}/download`
    : `/v1/analysis/export/excel?run_id=${runId}`
}
