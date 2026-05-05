(function () {
  function targetUrl(port, path) {
    return `${window.location.protocol}//${window.location.hostname}:${port}${path || ''}`;
  }

  document.querySelectorAll('[data-target-port]').forEach((link) => {
    const port = link.getAttribute('data-target-port');
    const path = link.getAttribute('data-target-path');
    if (port) {
      link.href = targetUrl(port, path);
    }
  });
})();
