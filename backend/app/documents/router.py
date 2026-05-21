import os
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_hr_or_admin
from app.core import config
from app.db.session import get_db
from app.documents.dependencies import get_storage_root
from app.documents.schemas import DocumentRead
from app.models.employee import Employee
from app.models.employee_document import DocumentType, EmployeeDocument
from app.models.user import User

router = APIRouter(prefix="/api/employees", tags=["documents"])


def _parse_doc_type(value: str) -> DocumentType:
    try:
        return DocumentType(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"invalid doc_type: {value}",
        )


@router.post(
    "/{employee_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    employee_id: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage_root: Path = Depends(get_storage_root),
    actor: User = Depends(get_current_hr_or_admin),
) -> EmployeeDocument:
    parsed_type = _parse_doc_type(doc_type)

    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found"
        )

    if file.content_type not in config.DOCUMENT_ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"unsupported content type: {file.content_type}",
        )

    data = await file.read()
    if len(data) > config.DOCUMENT_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="file exceeds 5 MB limit",
        )

    ext = os.path.splitext(file.filename or "")[1].lower()
    stored_name = f"{uuid.uuid4().hex}{ext}"
    relative_path = f"documents/{employee_id}/{stored_name}"
    full_path = storage_root / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)

    doc = EmployeeDocument(
        employee_id=employee_id,
        uploaded_by_id=actor.id,
        doc_type=parsed_type,
        file_name=file.filename or stored_name,
        content_type=file.content_type,
        size_bytes=len(data),
        storage_path=relative_path,
    )
    db.add(doc)
    db.flush()
    db.refresh(doc)
    return doc
