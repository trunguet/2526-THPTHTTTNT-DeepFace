(function () {
  const LOGIN_PAGE = 'login.html';
  const TOKEN_KEY = 'auth_token';
  const USER_KEY = 'admin_username';

  function isLoginPage() {
    return window.location.pathname.endsWith(`/${LOGIN_PAGE}`) || window.location.pathname.endsWith(LOGIN_PAGE);
  }

  function loginUrl() {
    const next = `${window.location.pathname}${window.location.search}`;
    return `./${LOGIN_PAGE}?next=${encodeURIComponent(next)}`;
  }

  function requireAdminSession() {
    if (isLoginPage()) return;
    if (!localStorage.getItem(TOKEN_KEY)) {
      window.location.replace(loginUrl());
    }
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
