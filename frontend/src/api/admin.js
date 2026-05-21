import api from '@/lib/api'

export async function listUsers() {
  const { data } = await api.get('/admin/users')
  return data
}

export async function createUser({ email, password, role }) {
  const { data } = await api.post('/admin/users', { email, password, role })
  return data
}

export async function updateUser(userId, payload) {
  const { data } = await api.patch(`/admin/users/${userId}`, payload)
  return data
}
