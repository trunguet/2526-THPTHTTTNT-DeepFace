(() => {
  const STORAGE_KEY = 'deepface_admin_sidebar_collapsed';
  const COLLAPSED_CLASS = 'sidebar-collapsed';

  const getAdminContainer = () => document.querySelector('.admin-container');

  const readCollapsed = () => {
    try {
      return localStorage.getItem(STORAGE_KEY) === '1';
    } catch {
      return false;
    }
  };

  const writeCollapsed = (collapsed) => {
    try {
      localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0');
    } catch {
      // ignore
    }
  };

  const applyCollapsed = (container, collapsed) => {
    container.classList.toggle(COLLAPSED_CLASS, collapsed);
    const toggle = document.querySelector('.sidebar-toggle');
    if (toggle) {
      toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
      toggle.setAttribute('aria-pressed', collapsed ? 'true' : 'false');
    }
  };

  const init = () => {
    const container = getAdminContainer();
    if (!container) return;

    const mq = window.matchMedia('(max-width: 768px)');

    const syncFromStorage = () => {
      // On mobile layout, sidebar becomes a top nav; keep it expanded.
      if (mq.matches) {
        applyCollapsed(container, false);
        return;
      }
      applyCollapsed(container, readCollapsed());
    };

    const toggleBtn = document.querySelector('.sidebar-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        const next = !container.classList.contains(COLLAPSED_CLASS);
        writeCollapsed(next);
        syncFromStorage();
      });
    }

    document.addEventListener('keydown', (event) => {
      // Alt+M toggles the sidebar (avoid common browser shortcuts).
      if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      if ((event.key || '').toLowerCase() !== 'm') return;
      const target = event.target;
      const tag = (target && target.tagName ? String(target.tagName) : '').toUpperCase();
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      event.preventDefault();
      const next = !container.classList.contains(COLLAPSED_CLASS);
      writeCollapsed(next);
      syncFromStorage();
    });

    if (mq.addEventListener) mq.addEventListener('change', syncFromStorage);
    else if (mq.addListener) mq.addListener(syncFromStorage);

    syncFromStorage();
  };

  document.addEventListener('DOMContentLoaded', init);
})();
