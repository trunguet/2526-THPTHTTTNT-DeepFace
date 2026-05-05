(function () {
  const ACCOUNT_PREFIX = 'deepface_admin_account:';
  const TOKEN_KEY = 'auth_token';
  const USER_KEY = 'admin_username';

  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const statusBox = document.getElementById('auth-status');
  const loginPanel = loginForm;
  const registerPanel = registerForm;
  const showLoginBtn = document.getElementById('show-login');
  const showRegisterBtn = document.getElementById('show-register');

  function accountKey(username) {
    return `${ACCOUNT_PREFIX}${username.trim().toLowerCase()}`;
  }

  function hasAnyAccount() {
    return Object.keys(localStorage).some((key) => key.startsWith(ACCOUNT_PREFIX));
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

  function randomToken() {
    const bytes = new Uint8Array(24);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
  }

  async function digest(value) {
    if (crypto.subtle) {
      const data = new TextEncoder().encode(value);
      const hash = await crypto.subtle.digest('SHA-256', data);
      return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, '0')).join('');
    }
    return btoa(unescape(encodeURIComponent(value)));
  }

  async function passwordHash(password, salt) {
    return digest(`${salt}:${password}`);
  }

  function saveSession(username) {
    localStorage.setItem(TOKEN_KEY, `admin-${randomToken()}`);
    localStorage.setItem(USER_KEY, username);
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
    if (localStorage.getItem(accountKey(username))) {
      showMessage('Tài khoản này đã tồn tại. Hãy đăng nhập.', 'warning');
      setMode('login');
      document.getElementById('login-username').value = username;
      return;
    }

    const salt = randomToken();
    const account = {
      username,
      salt,
      password_hash: await passwordHash(password, salt),
      created_at: new Date().toISOString(),
    };

    localStorage.setItem(accountKey(username), JSON.stringify(account));
    saveSession(username);
    showMessage('Đăng ký thành công. Đang chuyển vào Admin UI...', 'success');
    setTimeout(() => {
      window.location.href = nextUrl();
    }, 500);
  });

  loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const rawAccount = localStorage.getItem(accountKey(username));

    if (!rawAccount) {
      showMessage('Không tìm thấy tài khoản. Hãy đăng ký trước.', 'error');
      return;
    }

    const account = JSON.parse(rawAccount);
    const inputHash = await passwordHash(password, account.salt);

    if (inputHash !== account.password_hash) {
      showMessage('Mật khẩu không đúng.', 'error');
      return;
    }

    saveSession(account.username);
    showMessage('Đăng nhập thành công. Đang chuyển vào Admin UI...', 'success');
    setTimeout(() => {
      window.location.href = nextUrl();
    }, 500);
  });

  setMode(hasAnyAccount() ? 'login' : 'register');
})();
