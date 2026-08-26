/* ============================================================
   app.js — Hash-based SPA Router & Page Management
   ============================================================ */

(function () {
  'use strict';

  const app = document.getElementById('app');
  const navLinks = document.querySelectorAll('.nav-links a[data-page]');
  const navToggle = document.getElementById('nav-toggle');
  const navLinksContainer = document.getElementById('nav-links');

  // Page cache to avoid re-fetching
  const pageCache = {};

  // Track current page for cleanup
  let currentPage = null;

  // ── Mobile nav toggle ──────────────────────────────────────
  navToggle.addEventListener('click', () => {
    navLinksContainer.classList.toggle('open');
  });

  // Close mobile nav on link click
  navLinksContainer.addEventListener('click', (e) => {
    if (e.target.matches('a')) {
      navLinksContainer.classList.remove('open');
    }
  });

  // ── Route map ──────────────────────────────────────────────
  const routes = {
    about:    'pages/about.html',
    pipeline: 'pages/pipeline.html',
    map:      'pages/map.html',
    sources:  'pages/sources.html',
  };

  // ── Page init callbacks ────────────────────────────────────
  const pageInitCallbacks = {
    map: initMapPage,
    pipeline: initPipelinePage,
    about: initAboutPage,
    sources: initSourcesPage,
  };

  // ── Navigate to a page ─────────────────────────────────────
  async function navigateTo(page) {
    if (!routes[page]) page = 'about';

    // Cleanup previous page
    if (currentPage === 'map' && typeof destroyMap === 'function') {
      destroyMap();
    }

    // Update nav active state
    navLinks.forEach(link => {
      link.classList.toggle('active', link.dataset.page === page);
    });

    // Fetch or use cached HTML (skip cache for map — needs fresh canvas elements)
    if (!pageCache[page] || page === 'map') {
      try {
        const res = await fetch(routes[page]);
        if (!res.ok) throw new Error(`Failed to load ${page}`);
        pageCache[page] = await res.text();
      } catch (err) {
        app.innerHTML = `<div class="container section" style="text-align:center;">
          <h2>Page not found</h2>
          <p style="color:var(--text-secondary);">${err.message}</p>
        </div>`;
        currentPage = null;
        return;
      }
    }

    // Inject and animate
    app.innerHTML = `<div class="page-content">${pageCache[page]}</div>`;
    currentPage = page;

    // Run page-specific init
    if (pageInitCallbacks[page]) {
      pageInitCallbacks[page]();
    }

    // Scroll to top
    window.scrollTo(0, 0);
  }

  // ── Page initializers ──────────────────────────────────────

  function initAboutPage() {
    // Animate stat counters
    document.querySelectorAll('.stat-value[data-count]').forEach(el => {
      animateCounter(el, parseInt(el.dataset.count, 10));
    });

    // Scroll-reveal
    observeReveals();
  }

  function initPipelinePage() {
    observeReveals();
    if (typeof setupPipelineAnimations === 'function') {
      setupPipelineAnimations();
    }
  }

  function initMapPage() {
    // Small delay to let DOM settle, then init the map
    requestAnimationFrame(() => {
      if (typeof initSuitabilityMap === 'function') {
        initSuitabilityMap();
      }
    });
  }

  function initSourcesPage() {
    observeReveals();
  }

  // ── Counter animation ──────────────────────────────────────
  function animateCounter(el, target) {
    const duration = 1500;
    const startTime = performance.now();
    const suffix = el.dataset.suffix || '';

    function step(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      const current = Math.round(eased * target);
      el.textContent = current.toLocaleString() + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // ── Scroll-reveal observer ─────────────────────────────────
  function observeReveals() {
    const els = document.querySelectorAll('.reveal');
    if (!els.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    els.forEach(el => observer.observe(el));
  }

  // ── Hash change listener ───────────────────────────────────
  function onHashChange() {
    const hash = location.hash.replace('#', '') || 'about';
    navigateTo(hash);
  }

  window.addEventListener('hashchange', onHashChange);

  // ── Initial load ───────────────────────────────────────────
  onHashChange();
})();
