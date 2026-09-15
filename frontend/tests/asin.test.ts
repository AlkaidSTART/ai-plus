import { describe, expect, it } from 'bun:test'

const USER_EXAMPLE_URL =
  'https://www.amazon.com/Project-Cloud-Mens-Shoes-Lightweight/dp/B0FFW9LG7S/ref=trend_26_fall_ntos_grid?pf_rd_p=ec890b45-d55a-49b8-85e2-fa63c8255d5e&pf_rd_r=C9KT38048G6JX1QFHRT7&sr=1-2-a3f25ed3-e18f-4f84-9636-46feea37aaed&th=1&psc=1'

function extractAsinsClient(text: string): string[] {
  if (!text) return []
  const found: string[] = []
  const seen = new Set<string>()

  const add = (asin: string) => {
    const clean = asin.toUpperCase().trim()
    if (/^[A-Za-z0-9]{10}$/.test(clean) && !seen.has(clean)) {
      seen.add(clean)
      found.push(clean)
    }
  }

  // 1. URLs with /dp/ or /product/
  const urlRegex = /(?:dp|product|d)\/([A-Za-z0-9]{10})(?=[/?&#\s"']|$)/gi
  let match: RegExpExecArray | null
  while ((match = urlRegex.exec(text)) !== null) {
    add(match[1])
  }

  // 2. URL query param asin=
  const paramRegex = /[?&]asin=([A-Za-z0-9]{10})(?=[&#\s"']|$)/gi
  while ((match = paramRegex.exec(text)) !== null) {
    add(match[1])
  }

  // 3. Plain tokens
  const tokens = text.split(/[\s,，;；\n\r]+/)
  for (const token of tokens) {
    add(token)
  }

  return found
}

describe('Frontend ASIN extraction', () => {
  it('extracts ASIN from user example Amazon URL', () => {
    const res = extractAsinsClient(USER_EXAMPLE_URL)
    expect(res).toEqual(['B0FFW9LG7S'])
  })

  it('extracts multiple ASINs and URLs deduplicated', () => {
    const input = `
      ${USER_EXAMPLE_URL}
      https://www.amazon.com/dp/B0D5N57SHS
      b0052tbwm4
      B0FFW9LG7S
    `
    const res = extractAsinsClient(input)
    expect(res).toEqual(['B0FFW9LG7S', 'B0D5N57SHS', 'B0052TBWM4'])
  })

  it('handles query param asin=', () => {
    const res = extractAsinsClient('https://www.amazon.com/item?asin=B0CL4XJCJW')
    expect(res).toEqual(['B0CL4XJCJW'])
  })

  it('ignores invalid text', () => {
    const res = extractAsinsClient('not an asin, random words, 12345')
    expect(res).toEqual([])
  })
})
