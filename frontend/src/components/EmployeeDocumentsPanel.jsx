import { useCallback, useEffect, useRef, useState } from 'react'
import {
  deleteEmployeeDocument,
  downloadEmployeeDocument,
  listEmployeeDocuments,
  uploadEmployeeDocument,
} from '@/api/employees'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const DOC_TYPES = [
  { value: 'id_proof', label: 'ID proof' },
  { value: 'offer_letter', label: 'Offer letter' },
  { value: 'contract', label: 'Contract' },
  { value: 'other', label: 'Other' },
]

function formatBytes(n) {
  if (n == null) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(2)} MB`
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString()
}

export default function EmployeeDocumentsPanel({ employeeId }) {
  const [docs, setDocs] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [actionError, setActionError] = useState('')
  const [docType, setDocType] = useState('id_proof')
  const [file, setFile] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [busyDocId, setBusyDocId] = useState(null)
  const fileInputRef = useRef(null)

  const refresh = useCallback(async () => {
    setLoadError('')
    try {
      const data = await listEmployeeDocuments(employeeId)
      setDocs(data)
    } catch (err) {
      const detail = err?.response?.data?.detail
      setLoadError(detail || 'Could not load documents')
    }
  }, [employeeId])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function handleUpload(event) {
    event.preventDefault()
    if (!file) {
      setActionError('Pick a file first.')
      return
    }
    setIsUploading(true)
    setActionError('')
    try {
      await uploadEmployeeDocument(employeeId, { docType, file })
      setFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      await refresh()
    } catch (err) {
      const detail = err?.response?.data?.detail
      setActionError(detail || 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  async function handleDownload(doc) {
    setBusyDocId(doc.id)
    setActionError('')
    try {
      await downloadEmployeeDocument(employeeId, doc.id, doc.file_name)
    } catch (err) {
      const detail = err?.response?.data?.detail
      setActionError(detail || 'Download failed')
    } finally {
      setBusyDocId(null)
    }
  }

  async function handleDelete(doc) {
    if (!window.confirm(`Delete ${doc.file_name}?`)) return
    setBusyDocId(doc.id)
    setActionError('')
    try {
      await deleteEmployeeDocument(employeeId, doc.id)
      await refresh()
    } catch (err) {
      const detail = err?.response?.data?.detail
      setActionError(detail || 'Delete failed')
    } finally {
      setBusyDocId(null)
    }
  }

  return (
    <section className="space-y-4 rounded-lg border bg-card p-6">
      <div>
        <h2 className="text-base font-medium">Documents</h2>
        <p className="text-xs text-muted-foreground">
          PDF, PNG, or JPEG, up to 5&nbsp;MB.
        </p>
      </div>

      <form
        onSubmit={handleUpload}
        className="flex flex-wrap items-end gap-3 rounded-md border border-dashed p-4"
      >
        <div className="space-y-1">
          <Label htmlFor="doc-type">Type</Label>
          <select
            id="doc-type"
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            className="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
          >
            {DOC_TYPES.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="doc-file">File</Label>
          <Input
            id="doc-file"
            ref={fileInputRef}
            type="file"
            accept="application/pdf,image/png,image/jpeg"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
        <Button type="submit" size="sm" disabled={isUploading}>
          {isUploading ? 'Uploading...' : 'Upload'}
        </Button>
      </form>

      {actionError && (
        <div
          role="alert"
          className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
        >
          {actionError}
        </div>
      )}

      {loadError && (
        <div
          role="alert"
          className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
        >
          {loadError}
        </div>
      )}

      {!loadError && docs === null && (
        <p className="text-sm text-muted-foreground">Loading documents...</p>
      )}

      {!loadError && docs !== null && docs.length === 0 && (
        <p className="text-sm text-muted-foreground">No documents yet.</p>
      )}

      {!loadError && docs && docs.length > 0 && (
        <div className="overflow-hidden rounded-md border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">File</th>
                <th className="px-3 py-2 font-medium">Type</th>
                <th className="px-3 py-2 font-medium">Size</th>
                <th className="px-3 py-2 font-medium">Uploaded</th>
                <th className="px-3 py-2 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => {
                const rowBusy = busyDocId === doc.id
                return (
                  <tr key={doc.id} className="border-t">
                    <td className="px-3 py-2">{doc.file_name}</td>
                    <td className="px-3 py-2 capitalize">
                      {doc.doc_type.replace('_', ' ')}
                    </td>
                    <td className="px-3 py-2 text-muted-foreground tabular-nums">
                      {formatBytes(doc.size_bytes)}
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">
                      {formatDate(doc.uploaded_at || doc.created_at)}
                    </td>
                    <td className="px-3 py-2 text-right space-x-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={rowBusy}
                        onClick={() => handleDownload(doc)}
                      >
                        Download
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={rowBusy}
                        onClick={() => handleDelete(doc)}
                      >
                        Delete
                      </Button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
