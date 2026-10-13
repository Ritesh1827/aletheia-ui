/* TrustTrace mobile interactions: drawer, tabbar, tables->cards, share, sticky states. */
(function () {
  "use strict";

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  var lastToggleFocus = null;

  // ---- Drawer: Alpine owns navOpen when present; we sync class + scroll lock ----
  function shell() { return $(".shell"); }
  function alpineData(el) {
    try {
      if (window.Alpine && typeof window.Alpine.$data === "function") return window.Alpine.$data(el);
    } catch (e) { /* Alpine not ready */ }
    return null;
  }
  function applyNav(open, returnFocus) {
    var s = shell();
    if (!s) return;
    s.classList.toggle("nav-open", !!open);
    document.body.classList.toggle("nav-locked", !!open);
    var btn = $('[data-nav-toggle]');
    if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      var first = s.querySelector(".sidebar a.nav-item");
      if (first) setTimeout(function () { try { first.focus({ preventScroll: true }); } catch (e) { first.focus(); } }, 60);
    } else if (returnFocus && lastToggleFocus && lastToggleFocus.focus) {
      try { lastToggleFocus.focus({ preventScroll: true }); } catch (e) { lastToggleFocus.focus(); }
    }
  }
  function setNav(open) {
    var s = shell();
    if (!s) return;
    var d = alpineData(s);
    if (d && typeof d.navOpen !== "undefined") {
      d.navOpen = !!open; // Alpine :class binding flips the class; observer syncs lock
      applyNav(!!open, false); // immediate sync in case Alpine is slow
    } else {
      applyNav(open, false);
    }
  }
  function isNavOpen() {
    var s = shell();
    if (!s) return false;
    var d = alpineData(s);
    if (d && typeof d.navOpen !== "undefined") return !!d.navOpen;
    return s.classList.contains("nav-open");
  }

  document.addEventListener("click", function (ev) {
    var t = ev.target instanceof Element ? ev.target : null;
    if (!t) return;
    var toggle = t.closest("[data-nav-toggle]");
    if (toggle) {
      ev.preventDefault();
      lastToggleFocus = toggle;
      setNav(!isNavOpen());
      return;
    }
    if (t.closest("[data-nav-close]") || t.closest(".nav-scrim")) {
      setNav(false);
      return;
    }
    // Any sidebar nav link closes the drawer on mobile.
    if (t.closest(".sidebar a.nav-item") && window.innerWidth <= 900) {
      setNav(false);
    }
    // Mobile search toggle
    if (t.closest("[data-search-toggle]")) {
      var row = $(".searchbar--mobile");
      if (row) {
        var opening = !row.classList.contains("open");
        row.classList.toggle("open", opening);
        t.closest("[data-search-toggle]").setAttribute("aria-expanded", opening ? "true" : "false");
        if (opening) {
          var input = row.querySelector("input");
          if (input) setTimeout(function () { input.focus({ preventScroll: true }); }, 60);
        }
      }
    }
    // Back to top (honour reduced motion)
    if (t.closest("[data-to-top]")) {
      var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
    }
    // Share (Web Share API with clipboard fallback; resolve relative URLs)
    if (t.closest("[data-share]")) {
      var el = t.closest("[data-share]");
      var title = el.getAttribute("data-share-title") || document.title;
      var text = el.getAttribute("data-share-text") || "";
      var raw = el.getAttribute("data-share-url") || location.href;
      var url = raw;
      try { url = new URL(raw, location.origin).href; } catch (e) { url = raw; }
      if (navigator.share) {
        navigator.share({ title: title, text: text, url: url }).catch(function () {});
      } else if (window.copyText) {
        window.copyText(url, el);
      }
    }
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && isNavOpen()) setNav(false);
  });

  // Auto-close drawer when resizing up to desktop.
  window.addEventListener("resize", function () {
    if (window.innerWidth > 900 && isNavOpen()) setNav(false);
  });

  // Swipe left on the open drawer to close (touch).
  (function wireSwipe() {
    var startX = null;
    document.addEventListener("touchstart", function (ev) {
      if (!isNavOpen()) { startX = null; return; }
      var touch = ev.touches && ev.touches[0];
      startX = touch ? touch.clientX : null;
    }, { passive: true });
    document.addEventListener("touchend", function (ev) {
      if (startX === null || !isNavOpen()) return;
      var touch = ev.changedTouches && ev.changedTouches[0];
      if (touch && startX - touch.clientX > 64) setNav(false);
      startX = null;
    }, { passive: true });
  })();

  // Keep body scroll-lock + aria in sync when Alpine flips the class itself.
  function observeShell() {
    var s = shell();
    if (!s || !("MutationObserver" in window)) return;
    var obs = new MutationObserver(function () {
      var open = s.classList.contains("nav-open");
      document.body.classList.toggle("nav-locked", open);
      var btn = $('[data-nav-toggle]');
      if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
    obs.observe(s, { attributes: true, attributeFilter: ["class"] });
  }

  // ---- Tables -> cards: copy <th> text into td data-label ----
  function labelTables() {
    $all("table.queue").forEach(function (tbl) {
      var headers = $all("thead th", tbl).map(function (th) { return (th.textContent || "").trim(); });
      if (!headers.length) return;
      $all("tbody tr", tbl).forEach(function (tr) {
        $all("td", tr).forEach(function (td, i) {
          if (!td.hasAttribute("data-label") && headers[i]) td.setAttribute("data-label", headers[i]);
        });
      });
    });
  }

  // ---- Sticky topbar shadow + back-to-top visibility ----
  function onScroll() {
    var bar = $(".topbar");
    if (bar) bar.classList.toggle("is-stuck", window.scrollY > 4);
    var toTop = $("[data-to-top]");
    if (toTop) toTop.classList.toggle("show", window.scrollY > 600);
  }

  // ---- Carousel hint: hide once user scrolls the check rail ----
  function wireCarousels(root) {
    $all(".check-grid", root).forEach(function (grid) {
      if (grid.dataset.carouselWired) return;
      grid.dataset.carouselWired = "1";
      var hint = grid.parentElement ? grid.parentElement.querySelector(".carousel-hint") : null;
      if (!hint) return;
      grid.addEventListener("scroll", function () {
        if (grid.scrollLeft > 24) hint.style.opacity = "0";
      }, { passive: true });
    });
  }

  // ---- Mark pages with a mobile dock so content gets bottom padding ----
  function markDock() {
    if ($(".verify-dock")) document.body.classList.add("has-dock");
  }

  // ---- htmx partial swaps may inject new tables/carousels; re-wire them ----
  document.body.addEventListener("htmx:afterSwap", function (ev) {
    labelTables();
    wireCarousels(ev.target || document);
  });

  function init() {
    observeShell();
    labelTables();
    wireCarousels();
    markDock();
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  window.TrustTraceMobile = { setNav: setNav, labelTables: labelTables };
})();
