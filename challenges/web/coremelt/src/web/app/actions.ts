'use server'

// A single registered Server Action. Its only purpose is to make the RSC
// "Flight" action-handler surface live in the production build — that handler
// is the sink for CVE-2025-55182. The action itself is benign flavour.
export async function refreshTelemetry(_prev: unknown, _formData: FormData) {
  const jitter = () => Math.round(300 + Math.random() * 40)
  return {
    ok: true,
    ts: new Date().toISOString(),
    coreTempK: jitter(),
    note: 'Telemetry poll acknowledged by ICARUS RTU.',
  }
}
