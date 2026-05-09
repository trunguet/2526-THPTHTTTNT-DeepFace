(function () {
  const GATEWAY_PORTS = new Set(['', '80', '443', '8080']);

  function isGatewayMode() {
    return GATEWAY_PORTS.has(window.location.port || '');
  }

  function withCacheBust(url) {
    const value = String(url || '');
    if (!value) return value;
    const separator = value.includes('?') ? '&' : '?';
    return `${value}${separator}t=${Date.now()}`;
  }

  function targetUrl(port, path) {
    return `${window.location.protocol}//${window.location.hostname}:${port}${path || ''}`;
  }

  document.querySelectorAll('[data-target-port]').forEach((link) => {
    const port = link.getAttribute('data-target-port');
    const path = link.getAttribute('data-target-path');
    const gatewayPath = link.getAttribute('data-gateway-path');
    if (gatewayPath && isGatewayMode()) {
      link.href = gatewayPath;
      link.addEventListener('click', () => {
        link.href = withCacheBust(gatewayPath);
      });
      return;
    }
    if (port) {
      const directUrl = targetUrl(port, path);
      link.href = directUrl;
      link.addEventListener('click', () => {
        link.href = withCacheBust(directUrl);
      });
    }
  });
})();
