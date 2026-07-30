/* Dark mode, rotating tagline, scroll-reveal and back-to-top. Vanilla JS, no dependencies. */
(function () {
  "use strict";

  /* ---------- dark mode ---------- */
  var root = document.documentElement;
  var toggle = document.getElementById("theme-toggle");

  function applyTheme(theme) {
    if (theme === "dark") {
      root.setAttribute("data-theme", "dark");
    } else {
      root.removeAttribute("data-theme");
    }
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      var isDark = root.getAttribute("data-theme") === "dark";
      var next = isDark ? "light" : "dark";
      applyTheme(next);
      try { localStorage.setItem("theme", next); } catch (e) { /* storage unavailable */ }
    });
  }

  /* ---------- rotating tagline ---------- */
  var tagline = document.getElementById("author-tagline");
  if (tagline && tagline.dataset.rotate) {
    var phrases = tagline.dataset.rotate.split("|");
    var phraseIndex = 0;
    var charIndex = 0;
    var deleting = false;

    function typeTick() {
      var current = phrases[phraseIndex];
      if (!deleting) {
        charIndex++;
        tagline.textContent = current.slice(0, charIndex);
        if (charIndex === current.length) {
          deleting = true;
          setTimeout(typeTick, 1800);
          return;
        }
      } else {
        charIndex--;
        tagline.textContent = current.slice(0, charIndex);
        if (charIndex === 0) {
          deleting = false;
          phraseIndex = (phraseIndex + 1) % phrases.length;
        }
      }
      setTimeout(typeTick, deleting ? 35 : 55);
    }

    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      tagline.textContent = phrases[0];
    } else {
      setTimeout(typeTick, 400);
    }
  }

  /* ---------- scroll reveal ---------- */
  var revealTargets = document.querySelectorAll(".page__content h1, .paper-box");
  revealTargets.forEach(function (el) {
    el.classList.add("reveal-up");
  });

  if ("IntersectionObserver" in window) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );
    revealTargets.forEach(function (el) { observer.observe(el); });
  } else {
    revealTargets.forEach(function (el) { el.classList.add("no-observer"); });
  }

  /* ---------- open external links in a new tab ----------
     Replaces <base target="_blank">, which also hijacked same-page anchor
     links and made every nav jump open a new tab. */
  var links = document.querySelectorAll('a[href]');
  Array.prototype.forEach.call(links, function (a) {
    if (a.hasAttribute('target')) return;
    var href = a.getAttribute('href');
    if (!href || href.charAt(0) === '#') return;
    if (a.protocol !== 'http:' && a.protocol !== 'https:') return;
    if (a.host === window.location.host) return;
    a.setAttribute('target', '_blank');
    a.setAttribute('rel', 'noopener noreferrer');
  });

  /* ---------- back to top ---------- */
  var backToTop = document.getElementById("back-to-top");
  if (backToTop) {
    var toggleBackToTop = function () {
      if (window.scrollY > 500) {
        backToTop.classList.add("is-visible");
      } else {
        backToTop.classList.remove("is-visible");
      }
    };
    window.addEventListener("scroll", toggleBackToTop, { passive: true });
    toggleBackToTop();

    backToTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }
})();
