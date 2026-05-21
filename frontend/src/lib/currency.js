// Salaries are plain numbers in each employee's local currency. The
// currency code (ISO 4217) is on the API responses and is shown once
// per row in the Salary-by-country panel, so we don't prefix every
// amount with locale-specific symbols like "A$" or "CA$" that get
// noisy in a table.

export function formatSalary(amount) {
  if (amount == null || amount === '') return '—'
  const num = Number(amount)
  if (Number.isNaN(num)) return String(amount)
  return num.toLocaleString(undefined, { maximumFractionDigits: 0 })
}
