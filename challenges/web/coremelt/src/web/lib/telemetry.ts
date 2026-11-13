// Static flavour telemetry for the CoreWatch dashboard gauges.
// (The real sensor archive lives in corewatch.db — see DB_PATH in .env — but the
//  dashboard renders from this snapshot to avoid a DB round-trip on every paint.)
export type Gauge = { label: string; value: number; unit: string; pct: number; level: 'ok'|'warn'|'crit' }
export const gauges: Gauge[] = [
  { label: 'Core Temp',        value: 312,  unit: 'K',    pct: 61, level: 'ok'   },
  { label: 'Coolant Flow',     value: 4.8,  unit: 'm³/s', pct: 74, level: 'ok'   },
  { label: 'Neutron Flux',     value: 2.1,  unit: 'e14',  pct: 52, level: 'ok'   },
  { label: 'Containment PSI',  value: 128,  unit: 'kPa',  pct: 83, level: 'warn' },
  { label: 'Turbine RPM',      value: 3600, unit: 'rpm',  pct: 90, level: 'warn' },
  { label: 'Extraction Draw',  value: 97,   unit: '%',    pct: 97, level: 'crit' },
]
