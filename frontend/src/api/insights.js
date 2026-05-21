import api from '@/lib/api'

export async function getOverview() {
  const { data } = await api.get('/insights/overview')
  return data
}

export async function getSalaryByCountry() {
  const { data } = await api.get('/insights/salary/by-country')
  return data
}

export async function getSalaryByJobTitle({ country } = {}) {
  const params = country ? { country } : undefined
  const { data } = await api.get('/insights/salary/by-job-title', { params })
  return data
}

export async function getSalaryByDepartment() {
  const { data } = await api.get('/insights/salary/by-department')
  return data
}

export async function listEmployeeCountries() {
  const { data } = await api.get('/employees/countries')
  return data
}
