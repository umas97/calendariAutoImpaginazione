// calendariAutoImpaginazione -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// An export runs on the server in a thread (SPEC §8.7): start it, then ask how
// far it got until it is over. One at a time: the server says 409 otherwise.
import { useEffect, useState } from 'react'
import { api, ApiError, type ExportJob, type ExportRequest } from './api'

const POLL_MS = 300

export function useExportJob() {
  const [job, setJob] = useState<ExportJob | null>(null)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const running = job?.status === 'running'
  useEffect(() => {
    if (!job || job.status !== 'running') return
    let stopped = false
    const timer = window.setTimeout(async () => {
      try {
        const next = await api.exportJob(job.id)
        if (!stopped) setJob(next)
      } catch (err) {
        if (!stopped) {
          setError(err as ApiError)
          setJob({ ...job, status: 'failed', message: (err as Error).message })
        }
      }
    }, POLL_MS)
    return () => {
      stopped = true
      window.clearTimeout(timer)
    }
  }, [job])

  const start = async (body: ExportRequest) => {
    setStarting(true)
    setError(null)
    try {
      setJob(await api.startExport(body))
    } catch (err) {
      setError(err as ApiError)
    } finally {
      setStarting(false)
    }
  }

  return {
    job,
    running,
    starting,
    error,
    start,
    close: () => setJob(null),
  }
}
