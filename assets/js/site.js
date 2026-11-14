(function () {
  "use strict";
  var root = document.documentElement;
  var each = function (list, fn) { Array.prototype.forEach.call(list, fn); };

  // Theme: system -> light -> dark -> system.
  var themes = ["system", "light", "dark"];
  var button = document.querySelector(".theme-switch");
  var setTheme = function (t) {
    if (t === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", t);
    try {
      if (t === "system") localStorage.removeItem("theme");
      else localStorage.setItem("theme", t);
    } catch (e) { /* storage blocked: the choice lasts for this page */ }
    button.textContent = "Theme: " + t;
  };
  if (button) {
    var theme = root.getAttribute("data-theme") || "system";
    setTheme(theme);
    button.classList.add("is-ready");
    button.addEventListener("click", function () {
      theme = themes[(themes.indexOf(theme) + 1) % 3];
      setTheme(theme);
    });
  }

  // Tooltips for figure marks; the native <title> goes so that only one tip shows.
  var sel = ".fig [data-tip]";
  var marks = document.querySelectorAll(sel);
  if (marks.length) {
    var tip = document.createElement("div");
    tip.className = "tip";
    tip.setAttribute("role", "tooltip");
    tip.hidden = true;
    document.body.appendChild(tip);
    each(marks, function (m) {
      var t = m.querySelector(":scope > title");
      if (t) m.removeChild(t);
      if (!m.hasAttribute("aria-label")) m.setAttribute("aria-label", m.getAttribute("data-tip"));
      // A focusable mark needs a role of its own for the label to be exposed.
      if (!m.hasAttribute("role")) m.setAttribute("role", "img");
    });
    // Children of role="img" are presentational, which would hide the marks' names.
    each(document.querySelectorAll(".fig svg[role='img']"), function (s) {
      if (s.querySelector("[data-tip][tabindex]")) s.setAttribute("role", "group");
    });
    var show = function (el, x, y) {
      tip.textContent = el.getAttribute("data-tip");
      tip.hidden = false;
      var pad = 8, w = tip.offsetWidth, h = tip.offsetHeight;
      var vw = root.clientWidth, vh = root.clientHeight;
      var top = y - h - 12;
      if (top < pad) top = Math.min(y + 16, vh - h - pad);
      tip.style.left = Math.max(pad, Math.min(x + 12, vw - w - pad)) + "px";
      tip.style.top = top + "px";
    };
    var hide = function () { tip.hidden = true; };
    var mark = function (t) { return t && t.closest ? t.closest(sel) : null; };
    document.addEventListener("pointermove", function (e) {
      var el = mark(e.target);
      if (el) return show(el, e.clientX, e.clientY);
      var f = mark(document.activeElement);
      if (!f) return hide();
      var r = f.getBoundingClientRect();
      show(f, r.left + r.width / 2, r.top);
    }, { passive: true });
    document.addEventListener("focusin", function (e) {
      var el = mark(e.target);
      if (!el) return;
      var r = el.getBoundingClientRect();
      show(el, r.left + r.width / 2, r.top);
    });
    document.addEventListener("focusout", hide);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") hide(); });
    window.addEventListener("scroll", hide, { passive: true });
  }

  // Figure toggles: move is-on between the <g data-layer> groups of both drawings.
  each(document.querySelectorAll(".fig-toggles"), function (bar) {
    var fig = bar.closest(".fig");
    var select = function (name) {
      each(fig.querySelectorAll("svg [data-layer]"), function (g) {
        g.classList.toggle("is-on", g.getAttribute("data-layer") === name);
      });
      each(bar.querySelectorAll("button[data-show]"), function (b) {
        b.setAttribute("aria-pressed", String(b.getAttribute("data-show") === name));
      });
    };
    var on = fig.querySelector("svg [data-layer].is-on");
    if (on) select(on.getAttribute("data-layer"));
    bar.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-show]");
      if (b) select(b.getAttribute("data-show"));
    });
    bar.hidden = false;
  });

  // Table of contents: mark the section being read.
  var links = document.querySelectorAll(".toc a[href^='#']");
  if (!links.length || !("IntersectionObserver" in window)) return;
  var heads = [];
  each(links, function (a) {
    var h = document.getElementById(decodeURIComponent(a.hash.slice(1)));
    if (h && heads.indexOf(h) < 0) heads.push(h);
  });
  var seen = new Set();
  var current = function (id) {
    each(links, function (a) {
      if (decodeURIComponent(a.hash.slice(1)) === id) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    });
  };
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) seen.add(e.target);
      else seen.delete(e.target);
    });
    var h = heads.find(function (x) { return seen.has(x); }) ||
      heads.filter(function (x) { return x.getBoundingClientRect().top < 0; }).pop();
    if (h) current(h.id);
  }, { rootMargin: "0px 0px -60% 0px" });
  heads.forEach(function (h) { io.observe(h); });
})();
