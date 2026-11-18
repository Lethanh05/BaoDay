# Hợp đồng API Báo Đây

- **Đã triển khai:** đăng ký, đăng nhập, lấy thông tin tài khoản từ token.
- **Dùng để tích hợp:** bài viết và ảnh bìa. Thạnh phụ trách nền tảng, xác thực và tệp. Hòa phụ trách bài viết. Hai người cập nhật hợp đồng này khi thống nhất thay đổi.
- **Chờ Hòa rà soát:** URL đọc ảnh và mối liên kết giữa bài viết và ảnh bìa.

## Quy ước chung

- API có tiền tố `/api/v1`. Request và response JSON dùng `snake_case`. Mốc thời gian theo ISO 8601 ở UTC.
- API riêng nhận `Authorization: Bearer <access_token>`. JWT có thời hạn, tính bằng giây trong trường `expires_in`.
- Response cho một bản ghi dùng `{"data": {...}}`. Danh sách dùng `{"data": [...], "meta": {"page": 1, "page_size": 10, "total": 0, "total_pages": 0}}`. Xóa thành công trả `200` và `{"data": {"id": 1}}` với ID của bản ghi đã xóa.
- Response lỗi dùng `{"error": {"code": "VALIDATION_ERROR", "message": "Dữ liệu gửi lên không hợp lệ."}}`. Client xử lý theo mã HTTP và `error.code`. `error.message` dùng để hiển thị.
- ID là số nguyên dương. UUID/tên lưu trữ của ảnh là chi tiết nội bộ. Các trường cho phép bỏ trống được ghi rõ bên dưới.

| HTTP | Khi dùng |
| --- | --- |
| 200 | Đọc, đăng nhập, chỉnh sửa hoặc xóa thành công |
| 201 | Tạo tài khoản, bài viết hoặc tệp thành công |
| 401 | Sai thông tin đăng nhập, thiếu token, token sai hoặc hết hạn |
| 403 | Có token hợp lệ nhưng thiếu quyền |
| 404 | Tài nguyên không tồn tại hoặc bài nháp được truy cập qua API công khai |
| 409 | Email đã tồn tại hoặc ảnh đang được dùng làm bìa |
| 413 | Tệp vượt giới hạn dung lượng |
| 415 | Định dạng tệp không được hỗ trợ |
| 422 | Dữ liệu đầu vào không hợp lệ |

## Tài khoản

| Endpoint | Truy cập | Request | Response trong `data` |
| --- | --- | --- | --- |
| POST `/auth/register` | Công khai | `username`, `email`, `password` | User |
| POST `/auth/login` | Công khai | `email`, `password` | `access_token`, `token_type` (`bearer`), `expires_in`, `user` (User) |
| GET `/auth/me` | Bearer token | Không có body | User |

Các đường dẫn trong bảng được ghép với tiền tố chung.

**User:** `id`, `username`, `email`, `role`, `created_at`. Username dài 3–50 ký tự và được cắt khoảng trắng ở hai đầu. Mật khẩu đăng ký dài 8–128 ký tự. Email là duy nhất và được đối chiếu không phân biệt hoa thường. Role mặc định là `editor`; request đăng ký có trường `role` bị từ chối. Mật khẩu lưu bằng Argon2 và hash chỉ dùng nội bộ. Admin được tạo bằng lệnh local.

Mã lỗi xác thực: `EMAIL_EXISTS` (409), `INVALID_CREDENTIALS` (401), `UNAUTHORIZED` (401), `FORBIDDEN` (403) và `VALIDATION_ERROR` (422).

## Bài viết

| Endpoint | Truy cập | Request / kết quả |
| --- | --- | --- |
| GET `/articles` | Công khai | Query `page`, `page_size`. Trả danh sách bài `published`, mới xuất bản trước. |
| GET `/articles/{article_id}` | Công khai | Trả chi tiết bài `published`. |
| POST `/articles` | Editor, admin | Tạo bài từ các trường ghi bên dưới. Trả Article. |
| PATCH `/articles/{article_id}` | Tác giả, admin | Chỉ cập nhật trường được gửi. Trả Article. |
| DELETE `/articles/{article_id}` | Tác giả, admin | Trả ID bài đã xóa. |
| GET `/manage/articles` | Editor, admin | Tìm kiếm, lọc, sắp xếp và phân trang. Editor chỉ thấy bài của mình. |

- **Article:** `id`, `title`, `summary`, `content`, `status`, `author_id`, `cover_file_id`, `cover_url`, `created_at`, `updated_at`, `published_at`. Danh sách có thể bỏ `content`; chi tiết luôn trả `content`.
- **Tạo bài:** bắt buộc `title` và `content` là chuỗi không rỗng. `summary` và `cover_file_id` mặc định `null`. `status` nhận `draft` hoặc `published`, mặc định `draft`. Backend tự đặt ID, tác giả và các mốc thời gian.
- **Sửa bài:** nhận cùng nhóm trường có thể ghi. Gửi `cover_file_id: null` để gỡ ảnh bìa. Khi chuyển sang `published`, backend đặt `published_at`; khi đưa về `draft`, đặt lại `published_at` thành `null`.
- **Tìm kiếm và phân trang:** `q` tìm trong tiêu đề và tóm tắt; `status` lọc theo trạng thái; `sort_by` nhận `title`, `created_at` hoặc `updated_at` (mặc định `created_at`); `order` nhận `asc` hoặc `desc` (mặc định `desc`). `page` mặc định 1, `page_size` mặc định 10 và tối đa 100. Dùng ID để ổn định thứ tự khi trùng khóa sắp xếp.

## Tệp và ảnh bìa

| Endpoint | Truy cập | Request / kết quả |
| --- | --- | --- |
| POST `/files` | Editor, admin | Multipart với trường `file`. Nhận JPEG, PNG hoặc WebP, mặc định tối đa 5 MB. Trả File. |
| DELETE `/files/{file_id}` | Chủ tệp, admin | Trả ID tệp đã xóa. Nếu có bài đang dùng làm bìa, trả `409 FILE_IN_USE`. |
| GET `/files/{file_id}/content` *(đề xuất)* | Xem quy tắc bên dưới | Trả dữ liệu ảnh với `Content-Type` tương ứng. |

**File:** `id`, `original_name`, `url`, `mime_type`, `size_bytes`, `owner_id`, `created_at`. `storage_path` chỉ dùng nội bộ.

**Đề xuất tích hợp:** `Article.cover_file_id` tham chiếu `files.id` và cho phép `null`. Editor chỉ gắn ảnh mình sở hữu; admin có thể gắn ảnh bất kỳ. Thạnh cung cấp hàm kiểm tra quyền gắn ảnh khi triển khai module tệp. `cover_url` lấy từ `File.url`, là đường dẫn tương đối so với origin của API, hoặc `null` khi không có ảnh bìa. URL đọc được công khai khi ảnh gắn với ít nhất một bài `published`. Ảnh khác chỉ chủ tệp hoặc admin xem được bằng token. Mọi bài đang tham chiếu ảnh, kể cả bài nháp, đều chặn xóa ảnh.

## Đầu mối tích hợp Backend

| Import | Dùng để |
| --- | --- |
| `from app.db.base import Base` | Khai báo model SQLAlchemy |
| `from app.db.session import DbSession, get_db` | Nhận session theo request |
| `from app.core.dependencies import CurrentUser, get_current_user, require_roles` | Lấy tài khoản từ token hoặc kiểm tra vai trò |
| `from app.models.user import Role, User` | Dùng `Role.EDITOR`, `Role.ADMIN` và đặt khóa ngoại tới `users.id` |
| `from app.core.responses import ApiResponse, PageResponse, PaginationMeta, ErrorResponse` | Trả response và khai báo schema |
| `from app.core.errors import ApiError` | Trả lỗi bằng `ApiError(status_code, code, message)` |
| `from app.core.config import get_settings` | Đọc cấu hình dùng chung |

Router chỉ khai báo các đường dẫn tương đối như `/articles` và `/manage/articles`. `main.py` gắn tiền tố `/api/v1` khi đăng ký router. Hòa xuất `router` từ `app/api/v1/articles.py`. Thạnh tích hợp router, nạp model và thực hiện phần tệp theo hợp đồng đã chốt.

## Chạy phần xác thực trên Windows

Chạy từ thư mục gốc dự án với Python 3.11 trở lên.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Thay giá trị mẫu của `JWT_SECRET_KEY` trong `.env` bằng chuỗi vừa tạo. Khóa phải dài ít nhất 32 byte. Cơ sở dữ liệu SQLite cục bộ được tạo ở `backend/baoday.db` khi khởi động.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Mở [Swagger UI](http://127.0.0.1:8000/docs), gọi `/auth/register` rồi `/auth/login`. Dán giá trị `access_token` vào nút **Authorize** và gọi `/auth/me`.

Để tạo admin, chạy từ gốc dự án. Lệnh yêu cầu nhập mật khẩu trong terminal.

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m app.scripts.create_admin --username admin --email admin@example.com
Pop-Location
```
