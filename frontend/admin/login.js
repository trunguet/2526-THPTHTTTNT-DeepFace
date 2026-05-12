(function () {
  const TOKEN_KEY = 'auth_token';
  const USER_KEY = 'admin_username';

  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const statusBox = document.getElementById('auth-status');
  const loginPanel = loginForm;
  const registerPanel = registerForm;
  const showLoginBtn = document.getElementById('show-login');
  const showRegisterBtn = document.getElementById('show-register');
  const DIRECT_FRONTEND_PORTS = new Set(['3000', '3001', '3002']);

  function defaultApiBaseURL() {
    return DIRECT_FRONTEND_PORTS.has(window.location.port) ? 'http://localhost:18000' : '';
  }

  function showMessage(message, type) {
    statusBox.textContent = message;
    statusBox.className = `status-message status-${type}`;
    statusBox.style.display = 'block';
  }

  function setMode(mode) {
    const isLogin = mode === 'login';
    loginPanel.hidden = !isLogin;
    registerPanel.hidden = isLogin;
    showLoginBtn.classList.toggle('active', isLogin);
    showRegisterBtn.classList.toggle('active', !isLogin);
    statusBox.style.display = 'none';
  }

  function nextUrl() {
    const params = new URLSearchParams(window.location.search);
    const next = params.get('next');
    if (next && next.startsWith('/')) {
      return next;
    }
    return './index.html';
  }

  function saveSession(token, username) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, username);
  }

  async function apiPost(path, payload) {
    if (window.DeepFaceAPI?.post) {
      return window.DeepFaceAPI.post(path, payload);
    }

    const base = (window.DEEPFACE_API_BASE_URL || defaultApiBaseURL()).replace(/\/$/, '');
    const response = await fetch(`${base}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload ?? {}),
    });
    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) {
      const detail = typeof data === 'object' ? data.detail || data.message : data;
      throw new Error(detail || `HTTP ${response.status}`);
    }
    return data;
  }

  async function apiGet(path) {
    if (window.DeepFaceAPI?.get) {
      return window.DeepFaceAPI.get(path);
    }
    const base = (window.DEEPFACE_API_BASE_URL || defaultApiBaseURL()).replace(/\/$/, '');
    const response = await fetch(`${base}${path}`, { method: 'GET' });
    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) {
      const detail = typeof data === 'object' ? data.detail || data.message : data;
      throw new Error(detail || `HTTP ${response.status}`);
    }
    return data;
  }

  showLoginBtn.addEventListener('click', () => setMode('login'));
  showRegisterBtn.addEventListener('click', () => setMode('register'));

  registerForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const username = document.getElementById('register-username').value.trim();
    const password = document.getElementById('register-password').value;
    const confirm = document.getElementById('register-confirm').value;

    if (username.length < 3) {
      showMessage('Tên tài khoản cần ít nhất 3 ký tự.', 'error');
      return;
    }
    if (password.length < 6) {
      showMessage('Mật khẩu cần ít nhất 6 ký tự.', 'error');
      return;
    }
    if (password !== confirm) {
      showMessage('Mật khẩu xác nhận không khớp.', 'error');
      return;
    }

    try {
      const result = await apiPost('/api/auth/admin/register', { username, password });
      saveSession(result.token, result.username || username);
      showMessage('Đăng ký thành công. Đang chuyển vào Admin UI...', 'success');
    } catch (error) {
      showMessage(error.message || 'Đăng ký thất bại', 'error');
      return;
    }

    setTimeout(() => {
      window.location.href = nextUrl();
    }, 500);
  });

  loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    try {
      const result = await apiPost('/api/auth/admin/login', { username, password });
      saveSession(result.token, result.username || username);
      showMessage('Đăng nhập thành công. Đang chuyển vào Admin UI...', 'success');
    } catch (error) {
      showMessage(error.message || 'Đăng nhập thất bại', 'error');
      return;
    }

    setTimeout(() => {
      window.location.href = nextUrl();
    }, 500);
  });

  apiGet('/api/auth/admin/exists')
    .then((result) => setMode(result?.exists ? 'login' : 'register'))
    .catch(() => setMode('login'));
})();
