import api from '@/lib/api'

// Returns the canonical catalog: [{ name, currency }, …]. Use this for
// the create/edit employee dropdown so HR can add an employee in a
// country that doesn't yet have any other employees.
export async function listAllCountries() {
  const { data } = await api.get('/countries')
  return data
}
