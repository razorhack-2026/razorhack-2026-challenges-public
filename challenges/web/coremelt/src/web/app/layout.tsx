import './globals.css'
export const metadata = {
  title: 'CoreWatch | ICARUS Core Monitoring',
  description: 'RazerPowerCo — ICARUS reactor-core monitoring console',
}
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
