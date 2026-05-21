import api from '@/lib/api'

export async function listEmployees({
  q,
  department,
  country,
  includeInactive,
  limit = 20,
  offset = 0,
} = {}) {
  const params = { limit, offset }
  if (q) params.q = q
  if (department) params.department = department
  if (country) params.country = country
  if (includeInactive) params.include_inactive = true

  const { data } = await api.get('/employees', { params })
  return data
}

export async function listDepartments() {
  const { data } = await api.get('/employees/departments')
  return data
}
