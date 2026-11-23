import { api, remote } from "./api.js";

const $ = (id) => document.getElementById(id);
const pages = { home: $("home-view"), article: $("article-view"), manage: $("manage-view") };
const authForm = $("auth-form");
const editorForm = $("editor-form");
const uploadForm = $("upload-form");
const dayFormat = new Intl.DateTimeFormat("vi-VN", { day: "numeric", month: "long", year: "numeric" });
const todayFormat = new Intl.DateTimeFormat("vi-VN", { dateStyle: "full" });

function readStorage(key) {
  try { return sessionStorage.getItem(key); } catch { return null; }
}

function saveStorage(key, value) {
  try {
    if (value == null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, value);
  } catch { /* A private session can still use in-memory state. */ }
}

let token = readStorage("baoday.token");
let user = null;
let authMode = "login";
let homePage = 1;
let managePage = 1;
let filters = { q: "", status: "", sort_by: "created_at", order: "desc" };
let editingId = null;
let revision = 0;
let toastTimeout;
const objectUrls = new Set();
const recentMedia = new Map();

function element(tag, { className, text, href } = {}, ...children) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  if (href) node.href = href;
  node.append(...children.filter(Boolean));
  return node;
}

function button(label, action, className = "button button-outline") {
  const item = element("button", { className, text: label });
  item.type = "button";
  item.addEventListener("click", action);
  return item;
}

function textStatus(node, message) {
  node.textContent = message || "";
  node.hidden = !message;
}

function toast(message) {
  textStatus($("toast"), message);
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => textStatus($("toast"), ""), 4300);
}

function dateLabel(value) {
  const date = new Date(value);
  return value && !Number.isNaN(date.getTime()) ? dayFormat.format(date) : "";
}

function idOf(value) {
  if (!/^\d+$/.test(String(value))) return null;
  const id = Number(value);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

function route() {
  const hash = location.hash;
  const id = idOf(hash.startsWith("#bai-viet/") ? hash.slice(10) : "");
  if (hash.startsWith("#bai-viet/")) return { section: "article", id };
  return { section: hash === "#quan-ly" ? "manage" : "home" };
}

function newsLink(id) { return "#bai-viet/" + id; }
function canEdit() { return ["editor", "admin"].includes(user?.role); }

function imageSource(value, blob) {
  if (blob instanceof Blob) {
    const url = URL.createObjectURL(blob);
    objectUrls.add(url);
    return url;
  }
  if (typeof value !== "string" || !value) return null;
  try {
    const url = new URL(value, location.origin);
    return ["https:", "http:"].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

function imageBlock(item, { tag = "div", className = "", href, eager = false } = {}) {
  const block = element(tag, { href, className: "media " + className });
  const url = imageSource(item.cover_url, item.blob);
  if (href) block.setAttribute("aria-label", item.title || "Đọc bài");
  if (url) {
    const img = element("img");
    img.alt = "";
    img.loading = eager ? "eager" : "lazy";
    img.decoding = "async";
    img.referrerPolicy = "no-referrer";
    img.addEventListener("error", () => img.remove(), { once: true });
    img.src = url;
    block.append(img);
  }
  return block;
}

function leadArticle(article) {
  const href = newsLink(article.id);
  const copy = element("div", { className: "lead-copy" },
    element("span", { className: "kicker", text: "Tin nổi bật" }),
    element("h2", {}, element("a", { href, text: article.title })),
    article.summary && element("p", { text: article.summary }),
    element("a", { className: "lead-link", href, text: "Đọc bài viết →" }),
  );
  return element("article", { className: "lead" },
    imageBlock(article, { tag: "a", href, className: "lead-media", eager: true }), copy,
  );
}

function newsCard(article) {
  const href = newsLink(article.id);
  return element("article", { className: "card" },
    imageBlock(article, { tag: "a", href }),
    element("span", { className: "kicker", text: dateLabel(article.published_at) || "Tin mới" }),
    element("h3", {}, element("a", { href, text: article.title })),
    article.summary && element("p", { text: article.summary }),
  );
}

function renderPages(node, meta, change) {
  node.replaceChildren();
  node.hidden = (meta?.total_pages || 0) < 2;
  if (node.hidden) return;
  const previous = button("← Trước", () => change(meta.page - 1));
  const next = button("Sau →", () => change(meta.page + 1));
  previous.disabled = meta.page <= 1;
  next.disabled = meta.page >= meta.total_pages;
  node.append(previous, element("span", { text: "Trang " + meta.page + " / " + meta.total_pages }), next);
}

async function showHome(run) {
  const status = $("home-status");
  $("lead").replaceChildren();
  $("news-grid").replaceChildren();
  $("more-news").hidden = true;
  $("home-pages").hidden = true;
  textStatus(status, "Đang tải bản tin…");
  try {
    const { data, meta } = await remote.publicList({ page: homePage, page_size: 10 });
    if (run !== revision) return;
    if (!data.length && homePage > 1 && meta?.total_pages > 0) {
      homePage = meta.total_pages;
      render();
      return;
    }
    if (!data.length) {
      textStatus(status, "Chưa có bài viết được xuất bản.");
      return;
    }
    textStatus(status);
    const [featured, ...remaining] = data;
    $("lead").append(leadArticle(featured));
    if (remaining.length) {
      $("more-news").hidden = false;
      $("news-grid").append(...remaining.map(newsCard));
    }
    renderPages($("home-pages"), meta, (page) => {
      homePage = page;
      window.scrollTo(0, 0);
      render();
    });
  } catch (error) {
    if (run !== revision) return;
    textStatus(status, error.message);
  }
}

async function showArticle(run, id) {
  const status = $("article-status");
  const body = $("article-body");
  body.replaceChildren();
  if (!id) {
    textStatus(status, "Đường dẫn bài viết không hợp lệ.");
    return;
  }
  textStatus(status, "Đang tải bài viết…");
  try {
    const article = await remote.detail(id);
    if (run !== revision) return;
    textStatus(status);
    body.append(
      element("span", { className: "kicker", text: dateLabel(article.published_at) }),
      element("h1", { text: article.title }),
      article.summary ? element("p", { className: "summary", text: article.summary }) : "",
      article.cover_url ? imageBlock(article, { eager: true }) : "",
      element("div", { className: "story-content", text: article.content }),
    );
  } catch (error) {
    if (run === revision) textStatus(status, error.message);
  }
}

function mediaKey(id) { return "baoday.media." + id; }

function knownMedia(id) {
  if (!recentMedia.has(id)) {
    try {
      const items = JSON.parse(readStorage(mediaKey(id)) || "[]");
      recentMedia.set(id, Array.isArray(items) ? items : []);
    } catch {
      recentMedia.set(id, []);
    }
  }
  return recentMedia.get(id);
}

function rememberMedia(id, items) {
  recentMedia.set(id, items);
  saveStorage(mediaKey(id), JSON.stringify(items));
}

function articleRow(article) {
  const status = article.status === "published";
  const name = article.status === "published"
    ? element("a", { href: newsLink(article.id), text: article.title })
    : element("strong", { text: article.title });
  return element("tr", {},
    element("td", {}, name),
    element("td", {}, element("span", { className: "pill" + (status ? " published" : ""), text: status ? "Đã xuất bản" : "Bản nháp" })),
    element("td", { text: dateLabel(article.updated_at) }),
    element("td", {}, element("div", { className: "actions" },
      button("Sửa", (event) => actionOnce(event.currentTarget, () => openEditor(article))),
      button("Xóa", (event) => actionOnce(event.currentTarget, () => deleteArticle(article)), "button button-outline danger"),
    )),
  );
}

async function loadManageArticles(run) {
  const status = $("manage-status");
  $("manage-table").hidden = true;
  $("manage-pages").hidden = true;
  textStatus(status, "Đang tải bài viết…");
  try {
    const { data, meta } = await remote.managed({ ...filters, page: managePage, page_size: 10 }, token);
    if (run !== revision) return;
    if (!data.length && managePage > 1) {
      managePage = Math.max(1, meta?.total_pages || 1);
      render();
      return;
    }
    textStatus(status, data.length ? "" : "Không có bài viết phù hợp.");
    $("article-rows").replaceChildren(...data.map(articleRow));
    $("manage-table").hidden = !data.length;
    renderPages($("manage-pages"), meta, (page) => { managePage = page; render(); });
  } catch (error) {
    if (run !== revision) return;
    if (expireSession(error)) return;
    textStatus(status, error.message);
  }
}

function loadManageMedia(run) {
  const node = $("media-list");
  const files = knownMedia(user.id);
  node.replaceChildren();
  if (!files.length) node.append(element("p", { className: "muted", text: "Chưa tải ảnh trong phiên này." }));
  for (const file of files) {
    const preview = imageBlock({});
    node.append(element("div", { className: "media-item" }, preview,
      element("small", { text: "#" + file.id + " · " + file.original_name }),
      button("Xóa", (event) => actionOnce(event.currentTarget, () => deleteFile(file.id)), "button button-outline danger"),
    ));
    void loadPrivateImage(preview, file, token, run);
  }
}

async function loadPrivateImage(node, file, access, run) {
  try {
    const url = imageSource(file.url);
    if (!url || new URL(url).origin !== location.origin) return;
    const response = await fetch(url, {
      headers: { Authorization: "Bearer " + access },
      cache: "no-store",
      redirect: "error",
    });
    if (!response.ok || !/^image\/(jpeg|png|webp)(?:;|$)/.test(response.headers.get("content-type") || "")) return;
    const blob = await response.blob();
    if (run !== revision) return;
    node.replaceChildren(...imageBlock({ blob }).childNodes);
  } catch { /* A file can still be selected or removed by ID when preview is unavailable. */ }
}

function showManage(run) {
  const editable = canEdit();
  $("new-article").hidden = !editable;
  $("manage-gate").hidden = editable;
  $("manage-content").hidden = !editable;
  $("gate-login").hidden = Boolean(user);
  $("gate-message").textContent = user
    ? "Tài khoản hiện tại không có quyền biên tập."
    : "Đăng nhập để viết bài, quản lý bài viết và tải ảnh.";
  if (!editable) return;
  void loadManageArticles(run);
  loadManageMedia(run);
}

function render() {
  const run = ++revision;
  for (const url of objectUrls) URL.revokeObjectURL(url);
  objectUrls.clear();
  const { section, id } = route();
  for (const [key, view] of Object.entries(pages)) view.hidden = section !== key;
  $("nav-home").toggleAttribute("aria-current", section !== "manage");
  if (section !== "manage") $("nav-home").setAttribute("aria-current", "page");
  $("nav-manage").toggleAttribute("aria-current", section === "manage");
  if (section === "manage") $("nav-manage").setAttribute("aria-current", "page");
  $("account-name").textContent = user?.username || "";
  $("account-name").hidden = !user;
  $("account-action").textContent = user ? "Đăng xuất" : "Đăng nhập ↗";
  document.title = (section === "manage" ? "Quản lý bài viết · " : section === "article" ? "Bài viết · " : "") + "Báo Đây";
  if (section === "manage") showManage(run);
  else if (section === "article") void showArticle(run, id);
  else void showHome(run);
}

function showAuth(kind = "login", email = "") {
  authMode = kind;
  const register = kind === "register";
  const label = register ? "Đăng ký" : "Đăng nhập";
  authForm.reset();
  authForm.elements.email.value = email;
  $("auth-title").textContent = label;
  $("auth-submit").textContent = label;
  $("name-field").hidden = !register;
  authForm.elements.username.required = register;
  authForm.elements.password.minLength = register ? 8 : 1;
  authForm.elements.password.autocomplete = register ? "new-password" : "current-password";
  for (const tab of [$("login-tab"), $("register-tab")]) {
    const active = tab.id === kind + "-tab";
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-pressed", String(active));
  }
  textStatus($("auth-error"));
  if (!$("auth-dialog").open) $("auth-dialog").showModal();
  const field = register ? authForm.elements.username : authForm.elements.email;
  field.focus();
}

function endSession() {
  saveStorage("baoday.token", null);
  token = null;
  user = null;
  managePage = 1;
  for (const id of ["editor-dialog", "upload-dialog"]) $(id).close();
  render();
}

function expireSession(error) {
  if (error.status !== 401 || !token) return false;
  endSession();
  toast("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
  return true;
}

async function actionOnce(control, action, errorNode) {
  if (control?.disabled) return;
  if (control) control.disabled = true;
  if (errorNode) textStatus(errorNode);
  try {
    await action();
  } catch (error) {
    if (errorNode === $("auth-error") || !expireSession(error)) {
      if (errorNode) textStatus(errorNode, error.message);
      else toast(error.message);
    }
  } finally {
    if (control) control.disabled = false;
  }
}

function openEditor(article = null) {
  if (!canEdit() || route().section !== "manage") return;
  editingId = article?.id ?? null;
  editorForm.reset();
  for (const key of ["title", "summary", "content", "cover_file_id", "status"]) {
    editorForm.elements[key].value = article?.[key] ?? (key === "status" ? "draft" : "");
  }
  $("cover-options").replaceChildren(...knownMedia(user.id).map((file) => {
    const item = element("option", { text: file.original_name });
    item.value = file.id;
    return item;
  }));
  $("editor-title").textContent = article ? "Sửa bài viết" : "Soạn bài";
  textStatus($("editor-error"));
  $("editor-dialog").showModal();
}

async function deleteArticle(article) {
  if (!window.confirm("Xóa bài viết “" + article.title + "”?")) return;
  await remote.remove(article.id, token);
  toast("Đã xóa bài viết.");
  render();
}

async function deleteFile(id) {
  if (!id || !window.confirm("Xóa ảnh #" + id + "?")) return;
  const { id: accountId } = user;
  await remote.deleteFile(id, token);
  rememberMedia(accountId, knownMedia(accountId).filter((file) => file.id !== id));
  $("delete-file-form").reset();
  toast("Đã xóa ảnh #" + id + ".");
  render();
}

$("account-action").addEventListener("click", () => user ? endSession() : showAuth());
$("gate-login").addEventListener("click", () => showAuth());
$("login-tab").addEventListener("click", () => showAuth("login", authForm.elements.email.value));
$("register-tab").addEventListener("click", () => showAuth("register", authForm.elements.email.value));
$("new-article").addEventListener("click", (event) => actionOnce(event.currentTarget, () => openEditor()));
$("open-upload").addEventListener("click", () => {
  uploadForm.reset();
  textStatus($("upload-error"));
  $("upload-dialog").showModal();
});
document.querySelectorAll("[data-close]").forEach((control) => {
  control.addEventListener("click", () => control.closest("dialog").close());
});
document.querySelector(".skip").addEventListener("click", (event) => {
  event.preventDefault();
  $("noi-dung").focus();
});

authForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const kind = authMode;
  const body = Object.fromEntries(new FormData(authForm));
  void actionOnce($("auth-submit"), async () => {
    if (kind === "register") {
      await api("/auth/register", { method: "POST", body });
      showAuth("login", body.email);
      toast("Đã tạo tài khoản. Bạn có thể đăng nhập.");
      return;
    }
    delete body.username;
    const { data } = await api("/auth/login", { method: "POST", body });
    token = data.access_token;
    user = data.user;
    saveStorage("baoday.token", token);
    $("auth-dialog").close();
    render();
  }, $("auth-error"));
});

editorForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(editorForm));
  void actionOnce(editorForm.querySelector("button[type=submit], button:not([type])"), async () => {
    const content = values.content.trim();
    const title = values.title.trim();
    if (!title || !content) throw new Error("Nhập tiêu đề và nội dung bài viết.");
    const coverId = values.cover_file_id ? idOf(values.cover_file_id) : null;
    if (values.cover_file_id && !coverId) throw new Error("ID ảnh bìa phải là số nguyên dương.");
    const body = { title, content, summary: values.summary.trim() || null, status: values.status, cover_file_id: coverId };
    const creating = editingId == null;
    await remote.save(editingId, body, token);
    if (creating) managePage = 1;
    $("editor-dialog").close();
    toast(creating ? "Đã tạo bài viết." : "Đã cập nhật bài viết.");
    render();
  }, $("editor-error"));
});

uploadForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const { id: accountId } = user;
  const file = uploadForm.elements.file.files[0];
  if (!file) return;
  void actionOnce(uploadForm.querySelector("button:not([type])"), async () => {
    const image = await remote.upload(file, token);
    rememberMedia(accountId, [image, ...knownMedia(accountId)]);
    $("upload-dialog").close();
    toast("Đã tải ảnh lên. ID #" + image.id + ".");
    render();
  }, $("upload-error"));
});

$("delete-file-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const id = idOf(new FormData(event.currentTarget).get("id"));
  if (!id) return;
  void actionOnce(event.currentTarget.querySelector("button"), () => deleteFile(id));
});

$("filters").addEventListener("submit", (event) => {
  event.preventDefault();
  filters = Object.fromEntries(new FormData(event.currentTarget));
  filters.q = filters.q.trim();
  managePage = 1;
  render();
});

const today = new Date();
$("today").textContent = todayFormat.format(today);
$("today").dateTime = today.toISOString();
window.addEventListener("hashchange", () => {
  window.scrollTo(0, 0);
  render();
});

async function restoreSession() {
  if (!token) return;
  const saved = token;
  try {
    const { data } = await api("/auth/me", { token: saved });
    if (token === saved) {
      user = data;
      render();
    }
  } catch (error) {
    if (token === saved && !expireSession(error)) {
      token = null;
      saveStorage("baoday.token", null);
      toast(error.message);
    }
  }
}

render();
void restoreSession();
