import { describe, expect, it } from 'vitest'
import { formatDate, formatDuration, formatInt, formatPercent, formatRelativeTime, formatUsd } from './format'

describe('formatUsd', () => {
  it('格式化美元金额', () => {
    expect(formatUsd(42800)).toBe('$42,800.00')
    expect(formatUsd(29.9)).toBe('$29.90')
  })

  it('支持去掉符号', () => {
    expect(formatUsd(42800, false)).toBe('42,800.00')
  })

  it('空值返回占位符', () => {
    expect(formatUsd(null)).toBe('—')
    expect(formatUsd(undefined)).toBe('—')
    expect(formatUsd(Number.NaN)).toBe('—')
  })
})

describe('formatPercent', () => {
  it('比率转百分比', () => {
    expect(formatPercent(0.18)).toBe('18%')
    expect(formatPercent(0.1234, 1)).toBe('12.3%')
  })

  it('空值返回占位符', () => {
    expect(formatPercent(null)).toBe('—')
  })
})

describe('formatInt', () => {
  it('千分位格式化', () => {
    expect(formatInt(1234567)).toBe('1,234,567')
    expect(formatInt(0)).toBe('0')
  })

  it('空值返回占位符', () => {
    expect(formatInt(null)).toBe('—')
  })
})

describe('formatDuration', () => {
  it('秒级与分钟级', () => {
    expect(formatDuration(45)).toBe('45s')
    expect(formatDuration(90)).toBe('1m 30s')
    expect(formatDuration(120)).toBe('2m')
  })

  it('空值返回占位符', () => {
    expect(formatDuration(null)).toBe('—')
  })
})

describe('formatDate / formatRelativeTime', () => {
  it('非法输入返回原文', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatRelativeTime('not-a-date')).toBe('not-a-date')
  })

  it('相对时间近实时', () => {
    const now = new Date().toISOString()
    expect(formatRelativeTime(now)).toBe('刚刚')
  })

  it('过去几分钟', () => {
    const past = new Date(Date.now() - 3 * 60_000).toISOString()
    expect(formatRelativeTime(past)).toBe('3 分钟前')
  })
})
