/**
 * Mesh Gradient Background Animation
 * Advanced version with smooth linear movement, scaling, and breathing effects
 * Optimized for 60fps performance with GPU acceleration
 */

class MeshGradientBackground {
  constructor() {
    this.container = null;
    this.svg = null;
    this.blobs = [];
    this.animationFrameId = null;
    this.colors = ['#007069', '#10637D', '#2097BC', '#24937F', '#2C88A6', '#5CB0B0', '#7CC4ED'];
    this.init();
  }

  init() {
    this.createContainer();
    this.createSVG();
    this.createBlobs();
    // CSS animations handle the movement - no JS needed for linear movement
    // This ensures smooth 60fps performance with GPU acceleration
  }

  createContainer() {
    this.container = document.createElement('div');
    this.container.id = 'mesh-gradient-container';
    document.body.insertBefore(this.container, document.body.firstChild);
  }

  createSVG() {
    const svgNS = 'http://www.w3.org/2000/svg';
    this.svg = document.createElementNS(svgNS, 'svg');
    this.svg.setAttribute('viewBox', '0 0 1400 900');
    this.svg.setAttribute('preserveAspectRatio', 'xMidYMid slice');
    this.svg.style.willChange = 'transform';
    this.container.appendChild(this.svg);

    // Add defs for filters
    const defs = document.createElementNS(svgNS, 'defs');
    
    // Blur filter with 80px Gaussian blur for extreme glassmorphism
    const filter = document.createElementNS(svgNS, 'filter');
    filter.setAttribute('id', 'blur-filter');
    const feGaussianBlur = document.createElementNS(svgNS, 'feGaussianBlur');
    feGaussianBlur.setAttribute('in', 'SourceGraphic');
    feGaussianBlur.setAttribute('stdDeviation', '80');
    filter.appendChild(feGaussianBlur);
    defs.appendChild(filter);
    this.svg.appendChild(defs);
  }

  createBlobs() {
    const positions = [
      { cx: 200, cy: 200, r: 250 },
      { cx: 1000, cy: 300, r: 280 },
      { cx: 700, cy: 600, r: 220 },
      { cx: 300, cy: 700, r: 260 },
      { cx: 1100, cy: 700, r: 240 },
      { cx: 700, cy: 200, r: 270 },
      { cx: 500, cy: 500, r: 230 },
    ];

    const svgNS = 'http://www.w3.org/2000/svg';

    this.colors.forEach((color, index) => {
      const circle = document.createElementNS(svgNS, 'circle');
      circle.setAttribute('r', positions[index].r);
      circle.setAttribute('fill', color);
      circle.setAttribute('class', 'blob');
      circle.setAttribute('cx', positions[index].cx);
      circle.setAttribute('cy', positions[index].cy);
      circle.style.willChange = 'transform, opacity';

      this.svg.appendChild(circle);
      this.blobs.push({
        element: circle,
        color: color,
        baseX: positions[index].cx,
        baseY: positions[index].cy,
        radius: positions[index].r,
        z: index,
      });
    });

    // Randomize z-index layering for depth effect
    this.randomizeLayering();
  }

  /**
   * Randomize z-index layering for depth effect
   */
  randomizeLayering() {
    this.blobs.forEach((blob, index) => {
      blob.element.style.zIndex = Math.floor(Math.random() * this.blobs.length);
    });
  }

  /**
   * Update responsive layout
   */
  updateResponsive() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    
    const scale = Math.min(width, height) / 900;
    this.svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  }

  /**
   * Destroy the mesh gradient background
   */
  destroy() {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
    }
    if (this.container) {
      this.container.remove();
    }
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  const background = new MeshGradientBackground();

  // Handle window resize for responsive design
  window.addEventListener('resize', () => {
    background.updateResponsive();
  }, { passive: true });

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    background.destroy();
  });

  // Adjust scroll behavior for smooth scrolling
  document.addEventListener('scroll', () => {
    // Keep background fixed - no action needed
  }, { passive: true });
});
