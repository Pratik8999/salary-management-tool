import api from '@/lib/api'

export async function login({ email, password }) {
  const body = new URLSearchParams()
  body.append('username', email)
  body.append('password', password)

  const { data } = await api.post('/auth/login', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}
