from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, UploadFile, status
from fastapi.responses import FileResponse

from app.core.dependencies import OptionalUser, require_roles
from app.core.responses import ApiResponse
from app.db.session import DbSession
from app.models.user import Role, User
from app.schemas.file import FileRead
from app.services import files

router = APIRouter(prefix="/files", tags=["Ảnh"])
FileEditor = Annotated[User, Depends(require_roles(Role.EDITOR, Role.ADMIN))]
FileId = Annotated[int, Path(gt=0, le=2**63 - 1)]


@router.post("", status_code=status.HTTP_201_CREATED)
def upload_image(
    file: Annotated[UploadFile, File()],
    db: DbSession,
    user: FileEditor,
) -> ApiResponse[FileRead]:
    record = files.upload_file(db, file, user)
    return ApiResponse(data=FileRead.model_validate(record))


@router.get("/{file_id}/content", response_class=FileResponse)
def image_content(file_id: FileId, db: DbSession, user: OptionalUser) -> FileResponse:
    record, path = files.read_file(db, file_id, user)
    return FileResponse(
        path,
        media_type=record.mime_type,
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/{file_id}")
def remove_image(
    file_id: FileId, db: DbSession, user: FileEditor
) -> ApiResponse[dict[str, int]]:
    files.delete_file(db, file_id, user)
    return ApiResponse(data={"id": file_id})
