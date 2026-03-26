import { useState } from 'react'
import { Spinner } from './Spinner'

interface Props {
  useCases: string[]
  loading: boolean
  onSubmit: (useCase: string, maxItems: number | undefined, promptFile: File | undefined) => void
}

export function RunForm({ useCases, loading, onSubmit }: Props) {
  const [useCase, setUseCase] = useState(useCases[0] ?? '')
  const [maxItems, setMaxItems] = useState('')
  const [promptFile, setPromptFile] = useState<File | undefined>()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(useCase, maxItems ? parseInt(maxItems, 10) : undefined, promptFile)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Use case */}
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
          Use Case
        </label>
        <select
          value={useCase}
          onChange={e => setUseCase(e.target.value)}
          disabled={loading}
          className="input-field appearance-none cursor-pointer"
        >
          {useCases.map(uc => (
            <option key={uc} value={uc}>{uc}</option>
          ))}
        </select>
      </div>

      {/* Max items */}
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
          Max Items
          <span className="ml-1.5 normal-case font-normal text-gray-300">— optional</span>
        </label>
        <input
          type="number"
          min={1}
          value={maxItems}
          onChange={e => setMaxItems(e.target.value)}
          disabled={loading}
          placeholder="Process all rows"
          className="input-field"
        />
      </div>

      {/* Prompt file */}
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
          Prompt File
          <span className="ml-1.5 normal-case font-normal text-gray-300">— optional .txt override</span>
        </label>
        <label className={`flex items-center gap-3 rounded-lg border border-dashed border-gray-200 bg-gray-50 px-4 py-3 text-sm cursor-pointer transition-colors hover:border-brand-blue hover:bg-blue-50 ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}>
          <span className="text-brand-blue text-lg">📄</span>
          <span className="text-gray-500 flex-1 truncate">
            {promptFile ? promptFile.name : 'Choose a .txt file…'}
          </span>
          <input
            type="file"
            accept=".txt"
            onChange={e => setPromptFile(e.target.files?.[0])}
            disabled={loading}
            className="sr-only"
          />
          {promptFile && (
            <button
              type="button"
              onClick={e => { e.preventDefault(); setPromptFile(undefined) }}
              className="text-gray-300 hover:text-gray-500 text-xs"
            >
              ✕
            </button>
          )}
        </label>
      </div>

      {/* Divider */}
      <div className="border-t border-gray-100 pt-2" />

      <button
        type="submit"
        disabled={loading || !useCase}
        className="btn-primary w-full"
      >
        {loading
          ? <><Spinner className="h-4 w-4" /> Analysing — please wait…</>
          : <><span>▶</span> Run Analysis</>
        }
      </button>
    </form>
  )
}
