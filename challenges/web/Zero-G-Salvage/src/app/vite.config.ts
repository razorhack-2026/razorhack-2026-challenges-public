import tailwindcss from '@tailwindcss/vite'
import viteReact from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const config = defineConfig({
    plugins: [viteReact(), tailwindcss()],
    build: { minify: false },
    // Mirrors the nginx /api proxy so `npm run dev` stays same-origin too.
    server: { proxy: { '/api': 'http://127.0.0.1:3001' } },
})

export default config
