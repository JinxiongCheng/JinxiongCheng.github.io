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

  /* ---------- publication year timeline ----------
     Built from the papers already on the page, so adding an entry updates the
     rail without touching this file. */
  (function buildPublicationTimeline() {
    var heading = document.getElementById("publications");
    var papers = document.querySelectorAll(".paper-box[data-year]");
    if (!heading || papers.length < 2) return;

    var years = [];
    var counts = {};
    var firstOfYear = {};
    Array.prototype.forEach.call(papers, function (box) {
      var y = box.getAttribute("data-year");
      if (!counts[y]) {
        counts[y] = 0;
        years.push(y);
        firstOfYear[y] = box;
      }
      counts[y]++;
    });
    if (years.length < 2) return;

    var rail = document.createElement("nav");
    rail.className = "pub-rail";
    rail.setAttribute("aria-label", "Jump to publications by year");

    var line = document.createElement("span");
    line.className = "pub-rail__line";
    rail.appendChild(line);

    var items = years.map(function (y) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pub-rail__year";
      btn.setAttribute("data-year", y);
      btn.innerHTML =
        '<span class="pub-rail__dot"></span>' +
        '<span class="pub-rail__label">' + y + "</span>" +
        '<span class="pub-rail__count">' + counts[y] +
        (counts[y] === 1 ? " paper" : " papers") + "</span>";
      btn.addEventListener("click", function () {
        firstOfYear[y].scrollIntoView({
          behavior: prefersReducedMotion() ? "auto" : "smooth",
          block: "start"
        });
      });
      rail.appendChild(btn);
      return { year: y, btn: btn, box: firstOfYear[y] };
    });

    heading.parentNode.insertBefore(rail, heading.nextSibling);

    /* mark the year currently in view */
    function markActive() {
      var top = 0;
      var active = items[0];
      for (var i = 0; i < items.length; i++) {
        var r = items[i].box.getBoundingClientRect();
        if (r.top - 140 <= 0) active = items[i];
      }
      items.forEach(function (it) {
        it.btn.classList.toggle("is-active", it === active);
        if (it === active) it.btn.setAttribute("aria-current", "true");
        else it.btn.removeAttribute("aria-current");
      });
      return top;
    }
    markActive();
    window.addEventListener("scroll", markActive, { passive: true });
  })();

  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  /* ---------- Google Scholar stats ----------
     The numbers come from the google-scholar-stats branch that this repo's
     crawler workflow publishes. Reveal the block only once they arrive: that
     branch does not exist until the workflow has run, and a permanent "0"
     reads worse than showing nothing at all. */
  function normaliseTitle(s) {
    return String(s)
      .toLowerCase()
      .replace(/[‐-―]/g, "-")   // unicode dashes Scholar likes to use
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  var stats = document.getElementById("author-stats");
  if (stats && stats.getAttribute("data-gs-url") && window.fetch) {
    fetch(stats.getAttribute("data-gs-url"))
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (data) {
        if (!data) return;

        if (data.citedby) {
          document.getElementById("total_cit").textContent = data.citedby.toLocaleString();
          var h = document.getElementById("gs_hindex");
          if (data.hindex) {
            h.textContent = data.hindex;
          } else if (h && h.parentNode) {
            h.parentNode.remove();
          }
          stats.hidden = false;
        }

        /* Per-paper counts. The crawler keys publications by author_pub_id, but
           hard-coding those into the page means every new entry needs its id
           looked up by hand; match on the title instead so a paper added to the
           page picks up its count on the next crawl. */
        var pubs = data.publications || {};
        var byTitle = {};
        Object.keys(pubs).forEach(function (id) {
          var p = pubs[id];
          var title = p && p.bib && p.bib.title;
          if (title) byTitle[normaliseTitle(title)] = { id: id, cites: p.num_citations || 0 };
        });

        var scholarBase = "https://scholar.google.com/citations?view_op=view_citation&citation_for_view=";
        document.querySelectorAll(".paper-box").forEach(function (box) {
          var titleEl = box.querySelector(".paper-title");
          var slot = box.querySelector(".paper-cites");
          if (!titleEl || !slot) return;
          var hit = byTitle[normaliseTitle(titleEl.textContent)];
          if (!hit || !hit.cites) return;      // uncited or unmatched: stay hidden
          var a = document.createElement("a");
          a.href = scholarBase + encodeURIComponent(hit.id);
          a.target = "_blank";
          a.rel = "noopener";
          a.className = "paper-cites__link";
          a.textContent = "Cited by " + hit.cites;
          slot.appendChild(a);
          slot.hidden = false;
        });
      })
      .catch(function () { /* nothing published yet — leave it hidden */ });
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
