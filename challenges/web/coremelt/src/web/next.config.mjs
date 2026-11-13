/** CoreWatch — ICARUS reactor-core monitoring console.
 *  Pinned to next@15.0.3 / react@19.0.0 ON PURPOSE (CVE-2025-55182 "React2Shell").
 *  DO NOT run `npm update` — the challenge depends on the vulnerable RSC deserializer. */
const nextConfig = {
  reactStrictMode: true,
  // The dashboard is flavour; don't fail the production build on strict TS/lint
  // (react@19 stable vs next@15.0.3's RC-pinned types produce cosmetic diagnostics).
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },
}
export default nextConfig
