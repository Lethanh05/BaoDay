export class ApiError extends Error {
  constructor(status, message, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const endpoints = "/api/v1";

export async function api(path, { method = "GET", body, token } = {}) {
  const headers = { Accept: "application/json" };
  if (token) headers.Authorization = "Bearer " + token;
  if (body && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(endpoints + path, { method, headers, body, cache: "no-store" });
  } catch {
    throw new ApiError(0, "Không kết nối được máy chủ Báo Đây.");
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      payload?.error?.message || "Máy chủ không xử lý được yêu cầu.",
      payload?.error?.code,
    );
  }
  if (!payload || !Object.hasOwn(payload, "data")) {
    throw new ApiError(response.status, "Dữ liệu từ máy chủ chưa đúng hợp đồng API.");
  }
  return payload;
}

export function query(parameters) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(parameters)) {
    if (value !== "" && value != null) params.set(key, String(value));
  }
  return "?" + params.toString();
}

export const remote = {
  publicList(filters) { return api("/articles" + query(filters)); },
  async detail(id) { return (await api("/articles/" + id)).data; },
  managed(filters, token) { return api("/manage/articles" + query(filters), { token }); },
  async save(id, body, token) {
    const path = id == null ? "/articles" : "/articles/" + id;
    return (await api(path, { method: id == null ? "POST" : "PATCH", body, token })).data;
  },
  remove(id, token) { return api("/articles/" + id, { method: "DELETE", token }); },
  async upload(file, token) {
    const body = new FormData();
    body.append("file", file);
    return (await api("/files", { method: "POST", body, token })).data;
  },
  deleteFile(id, token) { return api("/files/" + id, { method: "DELETE", token }); },
};
