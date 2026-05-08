(function () {
  const DEFAULT_API_BASE_URL = 'http://localhost:18000';
  const API_STORAGE_KEY = 'deepface_api_base_url';

  function normalizeBaseURL(rawValue) {
    let value = String(rawValue || '').trim().replace(/\/$/, '');
    if (!value) return DEFAULT_API_BASE_URL;

    // Accept shorthand inputs from UI, e.g. ":18000" or "localhost:18000".
    if (value.startsWith(':')) {
      value = `http://localhost${value}`;
    } else if (!/^https?:\/\//i.test(value)) {
      value = `http://${value}`;
    }

    return value.replace(/\/$/, '');
  }

  function getBaseURL() {
    const raw =
      window.DEEPFACE_API_BASE_URL || localStorage.getItem(API_STORAGE_KEY) || '';
    const normalized = normalizeBaseURL(raw);

    // Auto-heal previously saved invalid shorthand values.
    const stored = localStorage.getItem(API_STORAGE_KEY);
    if (stored && stored !== normalized && !window.DEEPFACE_API_BASE_URL) {
      localStorage.setItem(API_STORAGE_KEY, normalized);
    }

    return normalized;
  }

  function setBaseURL(value) {
    const raw = String(value || '').trim();
    if (!raw) {
      localStorage.removeItem(API_STORAGE_KEY);
      return DEFAULT_API_BASE_URL;
    }
    const normalized = normalizeBaseURL(raw);
    localStorage.setItem(API_STORAGE_KEY, normalized);
    return normalized;
  }

  function getAuthToken() {
    return localStorage.getItem('auth_token') || '';
  }

  function escapeHTML(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatDateTime(value) {
    if (!value) return 'N/A';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'N/A';
    return date.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
  }

  function normalizeList(payload) {
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.items)) return payload.items;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.results)) return payload.results;
    return [];
  }

  async function request(path, options = {}) {
    const headers = new Headers(options.headers || {});
    const token = getAuthToken();

    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    if (
      options.body &&
      !(options.body instanceof FormData) &&
      !headers.has('Content-Type')
    ) {
      headers.set('Content-Type', 'application/json');
    }

    const response = await fetch(`${getBaseURL()}${path}`, {
      ...options,
      headers,
    });

    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json')
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const detail =
        typeof payload === 'object' ? payload.detail || payload.message : payload;
      throw new Error(detail || `HTTP ${response.status}`);
    }

    return payload;
  }

  window.DeepFaceAPI = {
    getBaseURL,
    setBaseURL,
    getAuthToken,
    escapeHTML,
    formatDateTime,
    normalizeList,
    request,
    get: (path, options) => request(path, { ...options, method: 'GET' }),
    post: (path, body, options = {}) =>
      request(path, {
        ...options,
        method: 'POST',
        body: body instanceof FormData ? body : JSON.stringify(body ?? {}),
      }),
    put: (path, body, options = {}) =>
      request(path, {
        ...options,
        method: 'PUT',
        body: JSON.stringify(body ?? {}),
      }),
    delete: (path, options) => request(path, { ...options, method: 'DELETE' }),
    health: () => request('/health'),
  };
})();
