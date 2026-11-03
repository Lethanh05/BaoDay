# Báo Đây

**Báo Đây** là website tin tức tiếng Việt. Độc giả xem tin đã xuất bản; người dùng đã xác thực quản lý bài viết và hình ảnh theo quyền được cấp. Frontend HTML, CSS và JavaScript thuần cung cấp giao diện đọc tin và thao tác với API.

## Mục tiêu dự án

- Xây dựng Backend Python có cấu trúc mô-đun, cấu hình qua biến môi trường và quy ước request/response thống nhất.
- Hoàn thiện các luồng đăng ký, đăng nhập, đọc tin công khai, quản lý bài viết và quản lý tệp.
- Áp dụng xác thực và phân quyền cho API riêng; kiểm tra quyền sở hữu bài viết và tệp.
- Xây dựng frontend tối giản để sử dụng và kiểm tra các chức năng Backend.

## Phạm vi MVP

| Khu vực | Chức năng |
|---|---|
| Tin công khai | Xem danh sách và nội dung chi tiết của bài viết đã xuất bản. |
| Tài khoản | Đăng ký, đăng nhập và sử dụng access token cho các yêu cầu cần xác thực. |
| Quản lý bài viết | Tạo, chỉnh sửa, xóa, tìm kiếm, lọc, sắp xếp và phân trang bài viết. |
| Quản lý tệp | Tải lên và xóa ảnh bài viết; kiểm tra loại và dung lượng tệp. |
| Giao diện | Hiển thị tin và cung cấp biểu mẫu cơ bản để thao tác với API. |

Editor quản lý bài viết của mình. Admin có thể quản lý mọi bài viết và tệp. Bài viết công khai phải có trạng thái `published`; bài mới mặc định ở trạng thái `draft`.

## Công nghệ

- Backend: Python, FastAPI.
- Frontend: HTML, CSS, JavaScript thuần; gọi API bằng Fetch.
- Cơ sở dữ liệu: SQLite dự kiến cho môi trường phát triển; cấu hình kết nối thông qua `DATABASE_URL`.
- Giao tiếp: REST API với JSON; upload tệp qua `multipart/form-data`.
- Xác thực: JWT Bearer token.

## API mục tiêu

| Phương thức | Endpoint | Truy cập | Mục đích |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Công khai | Tạo tài khoản; role mặc định là `editor`. |
| POST | `/api/v1/auth/login` | Công khai | Đăng nhập và nhận access token. |
| GET | `/api/v1/articles` | Công khai | Danh sách bài đã xuất bản; hỗ trợ phân trang. |
| GET | `/api/v1/articles/{article_id}` | Công khai | Chi tiết bài đã xuất bản. |
| POST | `/api/v1/articles` | Editor, admin | Tạo bài viết. |
| PATCH | `/api/v1/articles/{article_id}` | Tác giả, admin | Cập nhật bài viết. |
| DELETE | `/api/v1/articles/{article_id}` | Tác giả, admin | Xóa bài viết. |
| GET | `/api/v1/manage/articles` | Editor, admin | Tìm kiếm, lọc, sắp xếp và phân trang bài viết được phép quản lý. |
| POST | `/api/v1/files` | Editor, admin | Tải ảnh lên bằng trường multipart `file`. |
| DELETE | `/api/v1/files/{file_id}` | Chủ sở hữu, admin | Xóa tệp đã tải lên. |

Danh sách quản lý nhận các tham số `q`, `status`, `sort_by`, `order`, `page`, `page_size`. `sort_by` nhận `title`, `created_at` hoặc `updated_at`; `order` nhận `asc` hoặc `desc`.

## Mô hình dữ liệu chính

- User: `id`, `username`, `email`, `password_hash`, `role`, `created_at`. `password_hash` chỉ được lưu nội bộ, không trả về frontend. Tài khoản admin được khởi tạo riêng; API đăng ký không nhận role từ người dùng.
- Article: `id`, `title`, `summary`, `content`, `status`, `author_id`, `cover_file_id`, `created_at`, `updated_at`, `published_at`.
- File: `id`, `original_name`, `url`, `mime_type`, `size_bytes`, `owner_id`, `created_at`. Đường dẫn lưu trữ nội bộ không trả về frontend.

Tên trường JSON dùng `snake_case`; thời gian dùng ISO 8601. Response thành công dùng `data`; response danh sách có thêm `meta` gồm `page`, `page_size`, `total`, `total_pages`. Response lỗi dùng `error.code` và `error.message`.

## Cấu trúc mục tiêu

```text
BaoDay/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # auth.py, articles.py, files.py
│   │   ├── core/            # cấu hình, bảo mật, dependency, response
│   │   ├── db/              # Base và kết nối cơ sở dữ liệu
│   │   ├── models/          # user.py, article.py, file.py
│   │   ├── schemas/         # schema request/response
│   │   ├── services/        # xử lý nghiệp vụ
│   │   └── main.py
│   ├── uploads/             # tệp cục bộ khi phát triển
│   └── requirements.txt
├── frontend/
│   ├── css/
│   ├── js/
│   ├── pages/
│   └── index.html
├── .env.example
├── .gitignore
└── README.md
```

## Cấu hình và an toàn

Các cấu hình dự kiến gồm `APP_ENV`, `DATABASE_URL`, `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB`, `ALLOWED_UPLOAD_TYPES` và `CORS_ORIGINS`. Tạo `.env` từ `.env.example` khi chạy cục bộ; không commit `.env`, khóa bí mật hoặc tệp tải lên. Upload chỉ nhận JPEG, PNG và WebP; giới hạn mặc định 5 MB, có thể điều chỉnh bằng biến môi trường.

## Repository

[github.com/Lethanh05/BaoDay](https://github.com/Lethanh05/BaoDay)
