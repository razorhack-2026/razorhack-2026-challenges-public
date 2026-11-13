export const LIVE_UPDATE_INTERVAL_MS = 4000

const VOUCHER_REDEEMED_STORAGE_PREFIX = 'zgs-voucher-redeemed'

export function voucherRedeemedKey(sessionId: string) {
    return `${VOUCHER_REDEEMED_STORAGE_PREFIX}:${sessionId}`
}

export async function requestServer<T>(url: string): Promise<T> {
    const res = await fetch(url)
    if (!res.ok) {
        throw new Error(`Request to ${url} failed: ${res.status}`)
    }
    return res.json()
}

export async function postServer<T>(url: string, body?: unknown): Promise<T> {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    const data = await res.json().catch(() => null)
    if (!res.ok) {
        throw new Error(data?.error || `Request to ${url} failed: ${res.status}`)
    }
    return data
}

export function formatNumber(number: string) {
    const negative = number.startsWith('-')
    const [intPart, decimalPart] = (negative ? number.slice(1) : number).split('.')
    const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d)$)/g, ',')
    return (negative ? '-' : '') + grouped + (decimalPart ? `.${decimalPart}` : '')
}

export function formatCredits(credits: number) {
    return formatNumber(credits % 1.0 === 0.0 ? credits.toFixed(0) : credits.toFixed(2))
}

export function formatMillions(value: number) {
    return `${(value / 1_000_000).toFixed(1)}M`
}