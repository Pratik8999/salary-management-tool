from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.employee_document import DocumentType


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    uploaded_by_id: int
    doc_type: DocumentType
    file_name: str
    content_type: str
    size_bytes: int
    storage_path: str
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime
