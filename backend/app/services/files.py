import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import unauthorized
from app.core.errors import ApiError
from app.models.article import Article, ArticleStatus
from app.models.file import StoredFile
from app.models.user import Role, User

logger = logging.getLogger(__name__)
IMAGE_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
CHUNK_SIZE = 64 * 1024
MAX_IMAGE_PIXELS = 25_000_000


def _unsupported_image() -> ApiError:
    return ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "Tệp phải là ảnh JPEG, PNG hoặc WebP hợp lệ.")


def _detect_type(path: Path, allowed_types: list[str]) -> str:
    formats = [name for name, mime in IMAGE_TYPES.items() if mime in allowed_types]
    try:
        with Image.open(path, formats=formats) as image:
            if image.format is None or image.width * image.height > MAX_IMAGE_PIXELS:
                raise _unsupported_image()
            mime_type = IMAGE_TYPES[image.format]
            image.verify()
        with Image.open(path, formats=formats) as image:
            image.load()
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
        raise _unsupported_image() from exc
    return mime_type


def _file_too_large() -> ApiError:
    return ApiError(413, "FILE_TOO_LARGE", "Ảnh vượt quá giới hạn dung lượng.")


def _unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("Could not remove upload at %s", path.name)


def upload_file(db: Session, upload: UploadFile, user: User) -> StoredFile:
    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if upload.size is not None and upload.size > max_bytes:
        raise _file_too_large()

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    destination = settings.upload_dir / uuid4().hex
    temporary: Path | None = None
    moved = False
    try:
        size = 0
        with NamedTemporaryFile(dir=settings.upload_dir, suffix=".upload", delete=False) as output:
            temporary = Path(output.name)
            while chunk := upload.file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_bytes:
                    raise _file_too_large()
                output.write(chunk)

        mime_type = _detect_type(temporary, settings.allowed_upload_types)
        original_name = (upload.filename or "image").replace("\\", "/").rsplit("/", 1)[-1]
        record = StoredFile(
            original_name=original_name[:255] or "image",
            storage_path=destination.name,
            mime_type=mime_type,
            size_bytes=size,
            owner_id=user.id,
        )
        db.add(record)
        db.flush()
        temporary.replace(destination)
        moved = True
        db.commit()
        return record
    except Exception:
        db.rollback()
        if moved:
            _unlink(destination)
        raise
    finally:
        if temporary is not None:
            _unlink(temporary)


def _get_file(db: Session, file_id: int) -> StoredFile:
    record = db.get(StoredFile, file_id)
    if record is None:
        raise ApiError(404, "FILE_NOT_FOUND", "Không tìm thấy ảnh.")
    return record


def _ensure_owner(record: StoredFile, user: User) -> None:
    if user.role != Role.ADMIN and record.owner_id != user.id:
        raise ApiError(403, "FORBIDDEN", "Bạn không có quyền thao tác với ảnh này.")


def require_cover_file(db: Session, file_id: int, user: User) -> None:
    _ensure_owner(_get_file(db, file_id), user)


def read_file(db: Session, file_id: int, user: User | None) -> tuple[StoredFile, Path]:
    record = _get_file(db, file_id)
    published_article = db.scalar(
        select(Article.id)
        .where(Article.cover_file_id == file_id, Article.status == ArticleStatus.PUBLISHED)
        .limit(1)
    )
    if published_article is None:
        if user is None:
            raise unauthorized()
        _ensure_owner(record, user)
    path = get_settings().upload_dir / record.storage_path
    if not path.is_file():
        raise ApiError(404, "FILE_NOT_FOUND", "Không tìm thấy ảnh.")
    return record, path


def _file_in_use() -> ApiError:
    return ApiError(409, "FILE_IN_USE", "Ảnh đang được dùng làm bìa. Hãy gỡ ảnh khỏi bài viết trước.")


def delete_file(db: Session, file_id: int, user: User) -> None:
    record = _get_file(db, file_id)
    _ensure_owner(record, user)
    if db.scalar(select(Article.id).where(Article.cover_file_id == file_id).limit(1)) is not None:
        raise _file_in_use()

    path = get_settings().upload_dir / record.storage_path
    staged = path.with_suffix(".deleting")
    moved = False
    try:
        db.delete(record)
        try:
            # The foreign key also protects against a cover linked after the check above.
            db.flush()
        except IntegrityError as exc:
            raise _file_in_use() from exc

        try:
            path.replace(staged)
            moved = True
        except FileNotFoundError:
            # An already missing image can still have its database record removed.
            pass

        db.commit()
    except Exception:
        db.rollback()
        if moved:
            staged.replace(path)
        raise

    if moved:
        _unlink(staged)
