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

export async function getEmployee(employeeId) {
  const { data } = await api.get(`/employees/${employeeId}`)
  return data
}

export async function listEmployeeDocuments(employeeId) {
  const { data } = await api.get(`/employees/${employeeId}/documents`)
  return data
}

export async function uploadEmployeeDocument(employeeId, { docType, file }) {
  const form = new FormData()
  form.append('doc_type', docType)
  form.append('file', file)
  const { data } = await api.post(
    `/employees/${employeeId}/documents`,
    form,
  )
  return data
}

export async function deleteEmployeeDocument(employeeId, docId) {
  await api.delete(`/employees/${employeeId}/documents/${docId}`)
}

export async function downloadEmployeeDocument(employeeId, docId, fileName) {
  const response = await api.get(
    `/employees/${employeeId}/documents/${docId}/download`,
    { responseType: 'blob' },
  )
  const url = window.URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName || `document-${docId}`
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}
