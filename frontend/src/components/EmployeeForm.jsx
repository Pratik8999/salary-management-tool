import { useEffect, useState } from 'react'
import { listDepartments } from '@/api/departments'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const EMPLOYMENT_TYPES = [
  { value: 'full_time', label: 'Full-time' },
  { value: 'part_time', label: 'Part-time' },
  { value: 'contract', label: 'Contract' },
  { value: 'intern', label: 'Intern' },
]

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function validate(values) {
  const errors = {}
  if (!values.first_name.trim()) errors.first_name = 'Required'
  if (!values.last_name.trim()) errors.last_name = 'Required'
  if (!values.email.trim()) errors.email = 'Required'
  else if (!EMAIL_RE.test(values.email)) errors.email = 'Enter a valid email'
  if (!values.job_title.trim()) errors.job_title = 'Required'
  if (!values.country.trim()) errors.country = 'Required'
  if (!values.department_id) errors.department_id = 'Required'
  if (!values.date_joined) errors.date_joined = 'Required'
  else if (values.date_joined > todayIso())
    errors.date_joined = 'Cannot be in the future'
  const salaryNum = Number(values.salary)
  if (!values.salary) errors.salary = 'Required'
  else if (Number.isNaN(salaryNum) || salaryNum <= 0)
    errors.salary = 'Must be a positive number'
  return errors
}

const EMPTY = {
  first_name: '',
  last_name: '',
  email: '',
  job_title: '',
  country: '',
  salary: '',
  department_id: '',
  employment_type: 'full_time',
  date_joined: '',
}

export default function EmployeeForm({
  initialValues,
  onSubmit,
  onCancel,
  isSubmitting = false,
  serverError = '',
  submitLabel = 'Save',
}) {
  const [values, setValues] = useState(() => ({
    ...EMPTY,
    ...(initialValues || {}),
    salary: initialValues?.salary != null ? String(initialValues.salary) : '',
    department_id:
      initialValues?.department_id != null
        ? String(initialValues.department_id)
        : '',
  }))
  const [errors, setErrors] = useState({})
  const [departments, setDepartments] = useState([])
  const [departmentsError, setDepartmentsError] = useState('')

  useEffect(() => {
    let cancelled = false
    listDepartments()
      .then((data) => {
        if (cancelled) return
        setDepartments(data)
        // For an edit where the assigned department is no longer in the
        // active list, splice it in so the dropdown can still show it.
        if (
          initialValues?.department_id != null &&
          !data.some((d) => d.id === initialValues.department_id)
        ) {
          setDepartments((current) => [
            ...current,
            {
              id: initialValues.department_id,
              name: initialValues.department || `Department #${initialValues.department_id}`,
              is_active: false,
            },
          ])
        }
      })
      .catch((err) => {
        if (cancelled) return
        const detail = err?.response?.data?.detail
        setDepartmentsError(detail || 'Could not load departments')
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function setField(name, value) {
    setValues((v) => ({ ...v, [name]: value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    const next = validate(values)
    setErrors(next)
    if (Object.keys(next).length > 0) return
    onSubmit({
      ...values,
      salary: Number(values.salary),
      department_id: Number(values.department_id),
    })
  }

  return (
    <form noValidate onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          id="emp-first-name"
          label="First name"
          value={values.first_name}
          onChange={(v) => setField('first_name', v)}
          error={errors.first_name}
          disabled={isSubmitting}
        />
        <Field
          id="emp-last-name"
          label="Last name"
          value={values.last_name}
          onChange={(v) => setField('last_name', v)}
          error={errors.last_name}
          disabled={isSubmitting}
        />
        <Field
          id="emp-email"
          label="Email"
          type="email"
          value={values.email}
          onChange={(v) => setField('email', v)}
          error={errors.email}
          disabled={isSubmitting}
        />
        <Field
          id="emp-job-title"
          label="Job title"
          value={values.job_title}
          onChange={(v) => setField('job_title', v)}
          error={errors.job_title}
          disabled={isSubmitting}
        />
        <div className="space-y-1.5">
          <Label htmlFor="emp-department">Department</Label>
          <select
            id="emp-department"
            value={values.department_id}
            onChange={(e) => setField('department_id', e.target.value)}
            aria-invalid={Boolean(errors.department_id) || undefined}
            aria-describedby={
              errors.department_id ? 'emp-department-error' : undefined
            }
            disabled={isSubmitting || departments.length === 0}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          >
            <option value="">Select a department</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
                {d.is_active === false ? ' (inactive)' : ''}
              </option>
            ))}
          </select>
          {errors.department_id && (
            <p id="emp-department-error" className="text-xs text-destructive">
              {errors.department_id}
            </p>
          )}
          {departmentsError && (
            <p className="text-xs text-destructive">{departmentsError}</p>
          )}
          {!departmentsError && departments.length === 0 && (
            <p className="text-xs text-muted-foreground">
              No departments yet — ask an admin to create one.
            </p>
          )}
        </div>
        <Field
          id="emp-country"
          label="Country"
          value={values.country}
          onChange={(v) => setField('country', v)}
          error={errors.country}
          disabled={isSubmitting}
        />
        <Field
          id="emp-salary"
          label="Salary"
          type="number"
          step="0.01"
          min="0"
          value={values.salary}
          onChange={(v) => setField('salary', v)}
          error={errors.salary}
          disabled={isSubmitting}
        />
        <Field
          id="emp-date-joined"
          label="Date joined"
          type="date"
          value={values.date_joined}
          onChange={(v) => setField('date_joined', v)}
          error={errors.date_joined}
          disabled={isSubmitting}
        />
        <div className="space-y-1.5">
          <Label htmlFor="emp-employment-type">Employment type</Label>
          <select
            id="emp-employment-type"
            value={values.employment_type}
            onChange={(e) => setField('employment_type', e.target.value)}
            disabled={isSubmitting}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          >
            {EMPLOYMENT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {serverError && (
        <div
          role="alert"
          className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
        >
          {serverError}
        </div>
      )}

      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Saving...' : submitLabel}
        </Button>
      </div>
    </form>
  )
}

function Field({ id, label, error, disabled, type = 'text', value, onChange, ...rest }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        disabled={disabled}
        {...rest}
      />
      {error && (
        <p id={`${id}-error`} className="text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}
