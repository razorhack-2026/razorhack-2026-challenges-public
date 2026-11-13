import { gauges } from '../lib/telemetry'
import TelemetryPanel from './components/TelemetryPanel'
import EventLog from './components/EventLog'

// Navigation — "Overview" is the only live view. The others point at the
// privileged consoles that the ICARUS access layer keeps gated (they 404).
const NAV = [
  { label: 'Overview', href: '/', active: true },
  { label: 'Engineering', href: '/engineering' },
  { label: 'RTU Control', href: '/rtu' },
  { label: 'Admin', href: '/admin' },
]

export default function Dashboard() {
  return (
    <>
      <header>
        <div className="brand">
          <span className="logo">◈</span>
          <div>
            <h1>CoreWatch</h1>
            <span className="sub">ICARUS · Reactor-Core Monitoring System</span>
          </div>
        </div>
        <nav>
          {NAV.map((n) => (
            <a key={n.label} href={n.href} className={n.active ? 'on' : ''}>{n.label}</a>
          ))}
        </nav>
        <div className="ident">RazerPowerCo · session: <b>read-only</b></div>
      </header>

      <div className="alert">
        <span className="dot" /> CORE EXTRACTION ACTIVE — external RTU link established · coolant interlock <b>ENGAGED</b> · manual override requires engineering authorization
      </div>

      <main>
        <section className="top">
          <div className="corecard">
            <div className="cardhdr">REACTOR CORE · CONTAINMENT</div>
            <div className="reactor">
              <div className="ring r1" />
              <div className="ring r2" />
              <div className="ring r3" />
              <div className="core"><span>97%</span><small>EXTRACTION DRAW</small></div>
            </div>
            <div className="corestat">
              <span>FLUX <b className="ok">2.1e14</b></span>
              <span>TEMP <b className="warn">312 K</b></span>
              <span>STATE <b className="crit">DRAINING</b></span>
            </div>
          </div>

          <div className="gauges">
            <div className="cardhdr">SUBSYSTEM TELEMETRY</div>
            <div className="grid">
              {gauges.map((g) => (
                <div className="gauge" key={g.label}>
                  <div className="label">{g.label}</div>
                  <div className={`value ${g.level}`}>{g.value}<span className="unit">{g.unit}</span></div>
                  <div className="bar"><span className={g.level} style={{ width: `${g.pct}%` }} /></div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="controls">
          <div className="cardhdr">COOLANT INTERLOCK · MANUAL OVERRIDE <span className="lock">🔒 LOCKED</span></div>
          <div className="ctrlrow">
            <button disabled>SCRAM</button>
            <button disabled>Vent Coolant Loop</button>
            <button disabled>Release Interlock</button>
            <button disabled>Sever RTU Link</button>
            <span className="ctrlnote">Override sealed in the RTU ladder logic. Authorization key required — contact controls engineering.</span>
          </div>
        </section>

        <section className="bottom">
          <TelemetryPanel />
          <EventLog />
        </section>
      </main>

      <footer>
        CoreWatch v0.9.1 · ICARUS RTU link: <b className="ok">ONLINE</b> · unauthorized access is logged · © RazerPowerCo
      </footer>
    </>
  )
}
