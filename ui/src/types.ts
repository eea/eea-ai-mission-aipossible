export interface HealthResponse {
  status: string
  timestamp: string
  analysis_output_dir: string
}

export interface AnalysisRunItem {
  page_file: string
  output_file: string
  url: string
  saved: boolean
  elapsed_seconds: number | null
}

export interface AnalysisRunResponse {
  processed: number
  skipped: number
  total_elapsed_seconds: number
  total_elapsed_minutes: number
  provider: string
  model: string
  run_id: string
  output_dir: string
  items: AnalysisRunItem[]
  warnings: string[]
}
