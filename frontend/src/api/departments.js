import api from '@/lib/api'

export async function listDepartments({ includeInactive = false } = {}) {
  const params = includeInactive ? { include_inactive: true } : undefined
  const { data } = await api.get('/departments', { params })
  return data
}

export async function createDepartment({ name }) {
  const { data } = await api.post('/departments', { name })
  return data
}

export async function updateDepartment(departmentId, payload) {
  const { data } = await api.patch(`/departments/${departmentId}`, payload)
  return data
}
