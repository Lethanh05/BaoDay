import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.responses import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

HTTP_ERRORS = {
    400: ("BAD_REQUEST", "Yêu cầu không hợp lệ."),
    401: ("UNAUTHORIZED", "Cần đăng nhập để tiếp tục."),
    403: ("FORBIDDEN", "Bạn không có quyền thực hiện thao tác này."),
    404: ("NOT_FOUND", "Không tìm thấy tài nguyên."),
    405: ("METHOD_NOT_ALLOWED", "Phương thức không được hỗ trợ."),
    409: ("CONFLICT", "Dữ liệu bị xung đột."),
    413: ("FILE_TOO_LARGE", "Tệp vượt quá giới hạn dung lượng."),
    415: ("UNSUPPORTED_MEDIA_TYPE", "Loại tệp không được hỗ trợ."),
    422: ("VALIDATION_ERROR", "Dữ liệu gửi lên không hợp lệ."),
}


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers


def error_response(
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(body.model_dump(), status_code=status_code, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_invalid_request(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(422, *HTTP_ERRORS[422])

    @app.exception_handler(HTTPException)
    async def handle_http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        code, message = HTTP_ERRORS.get(
            exc.status_code, ("HTTP_ERROR", "Không thể xử lý yêu cầu.")
        )
        return error_response(exc.status_code, code, message, exc.headers)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled request error", exc_info=exc)
        return error_response(500, "INTERNAL_ERROR", "Máy chủ gặp lỗi khi xử lý yêu cầu.")
