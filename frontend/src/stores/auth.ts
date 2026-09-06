import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const AUTH_KEY = 'insightx.auth'
const USERS_KEY = 'insightx.users'

export interface AuthUser {
  email: string
  token: string
  loginAt: number
}

export interface StoredUser {
  email: string
  password: string
}

/** 注册 / 登录操作结果 */
export interface AuthResult {
  ok: boolean
  message: string
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function readJson<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

function readUsers(): StoredUser[] {
  return readJson<StoredUser[]>(USERS_KEY) ?? []
}

function readAuth(): AuthUser | null {
  const stored = readJson<AuthUser>(AUTH_KEY)
  // 兼容旧版 { username } 结构：视为未登录，需重新注册 / 登录
  if (!stored || !('email' in stored)) return null
  return stored
}

/**
 * Mock 登录态：注册用户表与登录态均存 localStorage，不涉及真实鉴权。
 * 演示环境请勿使用真实密码。
 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(readAuth())
  const isAuthenticated = computed(() => user.value !== null)
  const email = computed(() => user.value?.email ?? '')
  /** 展示用昵称：邮箱 @ 前缀 */
  const displayName = computed(() => email.value.split('@')[0] || email.value)

  function persist(u: AuthUser) {
    user.value = u
    localStorage.setItem(AUTH_KEY, JSON.stringify(u))
  }

  /** 注册：校验邮箱格式与密码强度，写入本地用户表 */
  function register(emailInput: string, password: string): AuthResult {
    const mail = emailInput.trim().toLowerCase()
    if (!EMAIL_RE.test(mail)) return { ok: false, message: '请输入有效的邮箱地址' }
    if (password.length < 6) return { ok: false, message: '密码至少需要 6 位' }
    const users = readUsers()
    if (users.some((u) => u.email === mail)) return { ok: false, message: '该邮箱已注册，请直接登录' }
    users.push({ email: mail, password })
    localStorage.setItem(USERS_KEY, JSON.stringify(users))
    return { ok: true, message: '' }
  }

  /** 登录：邮箱 + 密码需与注册记录一致 */
  function login(emailInput: string, password: string): AuthResult {
    const mail = emailInput.trim().toLowerCase()
    if (!EMAIL_RE.test(mail)) return { ok: false, message: '请输入有效的邮箱地址' }
    if (!password) return { ok: false, message: '请输入密码' }
    const found = readUsers().find((u) => u.email === mail)
    if (!found) return { ok: false, message: '该邮箱尚未注册，请先注册' }
    if (found.password !== password) return { ok: false, message: '邮箱或密码不正确' }
    persist({
      email: mail,
      token: `mock-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`,
      loginAt: Date.now(),
    })
    return { ok: true, message: '' }
  }

  function logout() {
    user.value = null
    localStorage.removeItem(AUTH_KEY)
  }

  return { user, isAuthenticated, email, displayName, register, login, logout }
})
