'use client'
import { useEffect, useRef, useState } from 'react'

// Flavour only: a fake ICARUS RTU event stream. No real data, no controls.
const LINES = [
  'RTU link handshake OK — remote endpoint authenticated',
  'coolant loop A pressure nominal (128 kPa)',
  'extraction draw holding at 97% — above advisory ceiling',
  'containment field stable — flux 2.1e14 n/cm²·s',
  'WARN: manual override requested — interlock sealed, denied',
  'turbine spool 3600 rpm — harmonic within tolerance',
  'core temperature 312 K — trending up (+0.4 K/min)',
  'WARN: unauthorized console probe from edge segment — logged',
  'ladder scan cycle complete — maint_override rung: locked',
  'telemetry archive flush → sensor_logs OK',
]

function stamp() {
  return new Date().toISOString().slice(11, 19)
}

export default function EventLog() {
  const [rows, setRows] = useState<string[]>(() => LINES.slice(0, 6).map((l) => `${stamp()}  ${l}`))
  const i = useRef(6)
  useEffect(() => {
    const t = setInterval(() => {
      setRows((prev) => {
        const next = `${stamp()}  ${LINES[i.current % LINES.length]}`
        i.current += 1
        return [...prev.slice(-7), next]
      })
    }, 2200)
    return () => clearInterval(t)
  }, [])
  return (
    <div className="panelbox log">
      <div className="cardhdr">ICARUS RTU · EVENT STREAM</div>
      <pre className="logbody">
        {rows.map((r, k) => (
          <div key={k} className={r.includes('WARN') ? 'warnline' : ''}>{r}</div>
        ))}
      </pre>
    </div>
  )
}
