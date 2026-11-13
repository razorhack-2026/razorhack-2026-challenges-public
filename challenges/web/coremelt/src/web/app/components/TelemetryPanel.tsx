'use client'
import { useActionState } from 'react'
import { refreshTelemetry } from '../actions'

const initial = { ok: false, ts: '', coreTempK: 0, note: 'Idle.' }

export default function TelemetryPanel() {
  const [state, formAction, pending] = useActionState(refreshTelemetry, initial)
  return (
    <div className="panelbox">
      <div className="label" style={{ fontSize: 11, color: '#6f8a80', letterSpacing: 1 }}>RTU TELEMETRY POLL</div>
      <form action={formAction} style={{ marginTop: 10 }}>
        <button type="submit" disabled={pending}>{pending ? 'Polling…' : 'Poll ICARUS RTU'}</button>
      </form>
      <pre style={{ marginTop: 12, color: '#6f8a80', fontSize: 12 }}>
        {state.ok ? `ack ${state.ts}  coreTempK=${state.coreTempK}\n${state.note}` : state.note}
      </pre>
    </div>
  )
}
