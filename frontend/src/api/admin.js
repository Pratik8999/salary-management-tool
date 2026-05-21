import api from '@/lib/api'

export async function listUsers() {
  const { data } = await api.get('/admin/users')
  return data
}
