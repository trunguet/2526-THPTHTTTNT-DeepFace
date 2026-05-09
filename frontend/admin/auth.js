(function () {
  const LOGIN_PAGE = 'login.html';
  const TOKEN_KEY = 'auth_token';
  const USER_KEY = 'admin_username';
  const API_STORAGE_KEY = 'deepface_api_base_url';
  const DEFAULT_API_BASE_URL = 'http://localhost:18000';

  function isLoginPage() {
    return window.location.pathname.endsWith(`/${LOGIN_PAGE}`) || window.location.pathname.endsWith(LOGIN_PAGE);
  }

  function loginUrl() {
    const next = `${window.location.pathname}${window.location.search}`;
    return `./${LOGIN_PAGE}?next=${encodeURIComponent(next)}`;
  }

  function requireAdminSession() {
    if (isLoginPage()) return;
    const token = localStorage.getItem(TOKEN_KEY) || '';
    if (!token) {
      window.location.replace(loginUrl());
      return;
    }

    const base = (localStorage.getItem(API_STORAGE_KEY) || DEFAULT_API_BASE_URL).replace(/\/$/, '');
    fetch(`${base}/api/auth/admin/me`, {
      method: 'GET',
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((response) => {
        if (response.ok) return;
        throw new Error('unauthorized');
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        window.location.replace(loginUrl());
      });
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    window.location.href = './login.html';
  }

  function currentUser() {
    return localStorage.getItem(USER_KEY) || 'Admin';
  }

  window.DeepFaceAdminAuth = {
    requireAdminSession,
    logout,
    currentUser,
  };

  requireAdminSession();
})();
