import { ApiError } from "./api.js";

const seed = [
  {
    title: "Tìm lại những khoảng xanh trong thành phố",
    topic: "Môi trường",
    summary: "Từ hàng cây trước nhà đến lối đi trong công viên, những khoảng xanh nhỏ góp phần làm dịu nhịp sống đô thị.",
    content: "Một bóng cây trên đường đi bộ có thể làm thay đổi cách chúng ta cảm nhận cả một khu phố. Những khoảng xanh gần nhà cũng tạo cơ hội để trẻ em vận động và người lớn gặp gỡ nhau.\n\nBản tin minh họa này gợi ý bắt đầu bằng những việc đơn giản: tìm một tuyến đường có bóng mát, quan sát cây xanh trong khu phố và chia sẻ những địa điểm công cộng dễ tiếp cận.",
    cover_url: "https://images.unsplash.com/photo-1514236986587-336693e36ec0?auto=format&fit=crop&w=1450&q=83",
  },
  {
    title: "Một buổi chiều ở thư viện",
    topic: "Văn hóa",
    summary: "Một chỗ ngồi yên tĩnh và vài trang sách có thể mở ra một nhịp sống khác.",
    content: "Thư viện là một trong số ít nơi bạn có thể dừng lại, đọc sách và học tập giữa ngày. Khi ghé một thư viện mới, hãy dành chút thời gian tìm hiểu giờ mở cửa, khu vực đọc và cách mượn sách.\n\nBạn có thể bắt đầu với một cuốn sách ngắn hoặc ghi lại những chủ đề muốn tìm hiểu trong lần ghé tiếp theo.",
    cover_url: "https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&w=720&q=78",
  },
  {
    title: "Sắp xếp lại góc làm việc số",
    topic: "Công nghệ",
    summary: "Vài thói quen đơn giản để dễ tìm tệp, bớt thông báo và tập trung hơn.",
    content: "Hãy bắt đầu bằng cách gom tệp theo dự án, sử dụng tên có ngày tháng và giữ một thư mục duy nhất cho tài liệu đang làm.\n\nCuối mỗi tuần, dành ít phút để dọn các tệp tạm và kiểm tra bản sao lưu của những tài liệu quan trọng.",
    cover_url: "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=720&q=78",
  },
  {
    title: "Đi bộ và lắng nghe một dòng sông",
    topic: "Đời sống",
    summary: "Một gợi ý cho buổi đi bộ cuối tuần có thêm thời gian ngắm cảnh.",
    content: "Chọn một lối đi ven sông có vỉa hè, bóng mát và chỗ nghỉ. Mang theo nước uống và tìm hiểu trước thời tiết để chuyến đi dễ chịu hơn.\n\nNếu đi cùng bạn bè, mỗi người có thể chọn một điều mình muốn quan sát: âm thanh, cây cối hoặc kiến trúc bên đường.",
    cover_url: "https://images.unsplash.com/photo-1437482078695-73f5ca6c96e2?auto=format&fit=crop&w=720&q=78",
  },
];

const limit = 5 * 1024 * 1024;
const collator = new Intl.Collator("vi", { sensitivity: "base" });
let database;

function openDatabase() {
  if (!database) {
    database = new Promise((resolve, reject) => {
      const request = indexedDB.open("baoday-editorial-demo", 1);
      request.onupgradeneeded = () => {
        const db = request.result;
        const articles = db.createObjectStore("articles", { keyPath: "id", autoIncrement: true });
        db.createObjectStore("files", { keyPath: "id", autoIncrement: true });
        seed.forEach((article, index) => {
          const date = new Date(Date.now() - index * 86400000).toISOString();
          articles.add({
            ...article, status: "published", author_id: 0, cover_file_id: null,
            created_at: date, updated_at: date, published_at: date,
          });
        });
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(new Error("Không mở được kho dữ liệu demo."));
      request.onblocked = () => reject(new Error("Hãy đóng các tab Báo Đây khác rồi tải lại."));
    }).catch((error) => {
      database = null;
      throw error;
    });
  }
  return database;
}

function result(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function transaction(names, mode, action) {
  const db = await openDatabase();
  const tx = db.transaction(names, mode);
  const done = new Promise((resolve, reject) => {
    tx.oncomplete = resolve;
    tx.onabort = () => reject(tx.error || new Error("Thao tác demo bị hủy."));
  });
  void done.catch(() => {});
  try {
    const data = await action(...names.map((name) => tx.objectStore(name)));
    await done;
    return data;
  } catch (error) {
    try { tx.abort(); } catch { /* Transaction already closed. */ }
    await done.catch(() => {});
    throw error;
  }
}

function requireEditor(user) {
  if (!["editor", "admin"].includes(user?.role)) {
    throw new ApiError(403, "Bạn không có quyền biên tập.");
  }
}

function checkOwner(user, id) {
  if (user.role !== "admin" && user.id !== id) {
    throw new ApiError(403, "Bạn không sở hữu mục này.");
  }
}

function cover(article, files) {
  return { ...article, cover_blob: files.get(article.cover_file_id)?.blob || null };
}

function paginate(items, { page = 1, page_size = 10 }) {
  return {
    data: items.slice((page - 1) * page_size, page * page_size),
    meta: { page, page_size, total: items.length, total_pages: Math.ceil(items.length / page_size) },
  };
}

function fold(value) {
  return value.toLocaleLowerCase("vi").normalize("NFD")
    .replace(/\p{M}/gu, "").replaceAll("đ", "d");
}

async function snapshot() {
  return transaction(["articles", "files"], "readonly", async (articles, files) => {
    const [rows, images] = await Promise.all([result(articles.getAll()), result(files.getAll())]);
    const imagesById = new Map(images.map((file) => [file.id, file]));
    return rows.map((article) => cover(article, imagesById));
  });
}

async function readImage(file) {
  if (file.size > limit) throw new ApiError(413, "Ảnh vượt quá 5 MB.");
  const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  const ascii = (from, to) => String.fromCharCode(...bytes.slice(from, to));
  let mime;
  if (bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255) mime = "image/jpeg";
  if (bytes[0] === 137 && ascii(1, 4) === "PNG" && bytes[4] === 13 && bytes[5] === 10) mime = "image/png";
  if (ascii(0, 4) === "RIFF" && ascii(8, 12) === "WEBP") mime = "image/webp";
  if (!mime) throw new ApiError(415, "Tệp phải là ảnh JPEG, PNG hoặc WebP.");
  return mime;
}

export const demo = {
  async publicList(filters) {
    const items = (await snapshot())
      .filter((article) => article.status === "published")
      .sort((a, b) => b.published_at.localeCompare(a.published_at) || b.id - a.id);
    return paginate(items, filters);
  },
  async detail(id) {
    const article = (await snapshot()).find((item) => item.id === id && item.status === "published");
    if (!article) throw new ApiError(404, "Không tìm thấy bài viết đã xuất bản.");
    return article;
  },
  async managed(filters, user) {
    requireEditor(user);
    const q = fold(filters.q || "");
    const items = (await snapshot()).filter((article) =>
      (user.role === "admin" || article.author_id === user.id)
      && (!filters.status || filters.status === article.status)
      && (!q || fold(article.title + " " + (article.summary || "")).includes(q)),
    );
    const direction = filters.order === "asc" ? 1 : -1;
    const key = filters.sort_by || "created_at";
    items.sort((a, b) => {
      const compared = key === "title"
        ? collator.compare(a.title, b.title)
        : a[key].localeCompare(b[key]);
      return direction * (compared || a.id - b.id);
    });
    return paginate(items, filters);
  },
  save(id, body, user) {
    requireEditor(user);
    return transaction(["articles", "files"], "readwrite", async (articles, files) => {
      const existing = id == null ? null : await result(articles.get(id));
      if (id != null && !existing) throw new ApiError(404, "Không tìm thấy bài viết.");
      if (existing) checkOwner(user, existing.author_id);
      if (body.cover_file_id != null) {
        const image = await result(files.get(body.cover_file_id));
        if (!image) throw new ApiError(404, "Không tìm thấy ảnh theo ID đã nhập.");
        checkOwner(user, image.owner_id);
      }
      const now = new Date().toISOString();
      const article = {
        ...existing, ...body,
        author_id: existing?.author_id ?? user.id,
        created_at: existing?.created_at ?? now,
        updated_at: now,
        published_at: body.status === "published" ? (existing?.published_at ?? now) : null,
      };
      if (body.cover_file_id !== existing?.cover_file_id) article.cover_url = null;
      const nextId = await result(articles.put(article));
      return { ...article, id: nextId };
    });
  },
  remove(id, user) {
    requireEditor(user);
    return transaction(["articles"], "readwrite", async (articles) => {
      const article = await result(articles.get(id));
      if (!article) throw new ApiError(404, "Không tìm thấy bài viết.");
      checkOwner(user, article.author_id);
      await result(articles.delete(id));
    });
  },
  media(user) {
    requireEditor(user);
    return transaction(["files"], "readonly", async (files) => {
      const all = await result(files.getAll());
      return all.filter((file) => user.role === "admin" || file.owner_id === user.id).reverse();
    });
  },
  async upload(file, user) {
    requireEditor(user);
    const mime = await readImage(file);
    return transaction(["files"], "readwrite", async (files) => {
      const image = {
        original_name: file.name, mime_type: mime, size_bytes: file.size,
        owner_id: user.id, created_at: new Date().toISOString(),
        blob: file.slice(0, file.size, mime),
      };
      const id = await result(files.add(image));
      return { ...image, id };
    });
  },
  deleteFile(id, user) {
    requireEditor(user);
    return transaction(["articles", "files"], "readwrite", async (articles, files) => {
      const file = await result(files.get(id));
      if (!file) throw new ApiError(404, "Không tìm thấy ảnh.");
      checkOwner(user, file.owner_id);
      const all = await result(articles.getAll());
      if (all.some((article) => article.cover_file_id === id)) {
        throw new ApiError(409, "Ảnh đang được dùng làm bìa. Hãy gỡ ảnh khỏi bài viết trước.", "FILE_IN_USE");
      }
      await result(files.delete(id));
    });
  },
};
