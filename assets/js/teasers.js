/* Animated publication teasers.

   Each teaser is an inline <svg class="teaser-anim"> built by
   _teasers/build_teasers.py. Elements carry their timing as data-t, a list of
   kind@start-end steps where start and end are fractions of one loop:

     fade   opacity 0 -> 1            out    opacity 1 -> 0
     rise   up from 10px below        pop    scale up from 40%
     slide  in from (data-dx, data-dy)
     appear fade in at (data-dx, data-dy), then wait for a move
     move   on to (data-mx, data-my); comma lists give successive moves
     grow   scaleX 0 -> 1 from the left edge (bars)
     draw   stroke drawn along the path (needs pathLength="1")
     path   glide along data-path, ending at the element's own position
     count  text counts up to data-to

   The markup itself is the finished picture, so without JS the figure is
   still complete. With reduced motion the timeline is parked on its poster
   frame (data-poster, default 0.9) instead of playing. Loops only run while
   the figure is on screen. */
(function () {
  "use strict";

  var teasers = document.querySelectorAll(".teaser-anim");
  if (!teasers.length || !Element.prototype.animate) return;

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function parse(spec) {
    return spec.trim().split(/\s+/).map(function (tok) {
      var m = /^(\w+)@([\d.]+)-([\d.]+)$/.exec(tok);
      if (!m) return null;
      return { kind: m[1], s: +m[2], e: +m[3] };
    }).filter(Boolean);
  }

  function num(el, name, dflt, k) {
    var v = el.getAttribute("data-" + name);
    if (v === null) return dflt;
    var parts = v.split(",");   // successive move steps read successive values
    return +parts[Math.min(k || 0, parts.length - 1)];
  }

  // Motion eases in and out; pops overshoot a touch, like something landing.
  var EASE = "cubic-bezier(.45, 0, .25, 1)";
  var POP = "cubic-bezier(.34, 1.45, .64, 1)";

  function easeInOut(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  // Build one keyframe track for a property from a list of
  // [start, end, from, to, easing?] steps, holding the value between steps.
  function track(prop, init, steps) {
    var frames = [{ offset: 0 }];
    frames[0][prop] = init;
    var cur = init;
    steps.sort(function (x, y) { return x[0] - y[0]; }).forEach(function (st) {
      var a = {}, b = {};
      a.offset = st[0]; a[prop] = st[2]; a.easing = st[4] || EASE;
      b.offset = st[1]; b[prop] = st[3];
      // hold the previous value up to this step's start
      var hold = {}; hold.offset = st[0]; hold[prop] = cur;
      if (st[2] !== cur) frames.push(hold);
      frames.push(a, b);
      cur = st[3];
    });
    var last = { offset: 1 }; last[prop] = cur;
    frames.push(last);
    return frames;
  }

  function setup(svg) {
    var dur = num(svg, "dur", 10000);
    var anims = [];
    var counters = [];

    function add(el, frames) {
      anims.push(el.animate(frames, { duration: dur, iterations: Infinity, fill: "both" }));
    }

    svg.querySelectorAll("[data-t]").forEach(function (el) {
      var steps = parse(el.getAttribute("data-t"));
      if (!steps.length) return;

      var op = [], tf = [], dash = [];
      var opInit = null, tfInit = null;
      var at = "translate(0px, 0px)";   // where the element sits after the last move
      var moves = 0;

      steps.forEach(function (st) {
        switch (st.kind) {
          case "fade":
          case "count":
            if (opInit === null) opInit = "0";
            op.push([st.s, st.e, "0", "1"]);
            if (st.kind === "count") counters.push({ el: el, s: st.s, e: st.e, to: num(el, "to", 0) });
            break;
          case "out":
            if (opInit === null) opInit = "1";
            op.push([st.s, st.e, "1", "0"]);
            break;
          case "rise":
          case "pop":
          case "slide":
            var from = st.kind === "rise" ? "translate(0px, 10px)"
              : st.kind === "pop" ? "scale(0.4)"
              : "translate(" + num(el, "dx", 0) + "px, " + num(el, "dy", 0) + "px)";
            var to = st.kind === "pop" ? "scale(1)" : "translate(0px, 0px)";
            if (tfInit === null) tfInit = from;
            tf.push([st.s, st.e, from, to, st.kind === "pop" ? POP : EASE]);
            if (opInit === null) opInit = "0";
            op.push([st.s, Math.min(st.e, st.s + (st.e - st.s) * 0.6), "0", "1"]);
            at = to;
            break;
          case "appear":
            // fade in at (data-dx, data-dy) and wait there for a later move
            at = "translate(" + num(el, "dx", 0) + "px, " + num(el, "dy", 0) + "px)";
            if (tfInit === null) tfInit = at;
            if (opInit === null) opInit = "0";
            op.push([st.s, st.e, "0", "1"]);
            break;
          case "move":
            var dest = "translate(" + num(el, "mx", 0, moves) + "px, " + num(el, "my", 0, moves) + "px)";
            moves++;
            if (tfInit === null) tfInit = at;
            tf.push([st.s, st.e, at, dest]);
            at = dest;
            break;
          case "path":
            // follow data-path (user units) and finish where the markup puts
            // the element, i.e. at the path's end. Sampled at eased distances
            // and joined linearly, so the glide accelerates and settles.
            var guide = document.createElementNS("http://www.w3.org/2000/svg", "path");
            guide.setAttribute("d", el.getAttribute("data-path"));
            guide.setAttribute("fill", "none");
            svg.appendChild(guide);
            var len = guide.getTotalLength();
            var end = guide.getPointAtLength(len);
            var pts = [];
            for (var i = 0; i <= 24; i++) {
              var p = guide.getPointAtLength(len * easeInOut(i / 24));
              pts.push("translate(" + (p.x - end.x).toFixed(2) + "px, " + (p.y - end.y).toFixed(2) + "px)");
            }
            svg.removeChild(guide);
            if (tfInit === null) tfInit = pts[0];
            for (var j = 0; j < 24; j++) {
              var a0 = st.s + (st.e - st.s) * j / 24, a1 = st.s + (st.e - st.s) * (j + 1) / 24;
              tf.push([a0, a1, pts[j], pts[j + 1], "linear"]);
            }
            at = pts[24];
            break;
          case "grow":
            el.style.transformOrigin = "left center";
            if (tfInit === null) tfInit = "scaleX(0)";
            tf.push([st.s, st.e, "scaleX(0)", "scaleX(1)"]);
            break;
          case "draw":
            // a gap longer than the path, and a start just past it, so a round
            // cap does not leave a dot at either end before the line is drawn
            if (dash.length === 0) el.style.strokeDasharray = "1 2";
            dash.push([st.s, st.e, "1.02", "0"]);
            break;
        }
      });

      if (op.length) add(el, track("opacity", opInit, op));
      if (tf.length) add(el, track("transform", tfInit, tf));
      if (dash.length) add(el, track("strokeDashoffset", "1.02", dash));
    });

    counters.forEach(function (c) {
      c.fmt = c.el.textContent.replace(/[\d,]+/, "#");
    });

    var state = { svg: svg, dur: dur, anims: anims, counters: counters, running: false };
    svg.classList.add("t-ready");
    seek(state, num(svg, "poster", 0.9));
    return state;
  }

  function seek(state, frac) {
    var t = frac * state.dur;
    state.anims.forEach(function (a) { a.pause(); a.currentTime = t; });
    paint(state, frac);
  }

  function paint(state, frac) {
    state.counters.forEach(function (c) {
      var p = Math.max(0, Math.min(1, (frac - c.s) / (c.e - c.s)));
      var n = Math.round(c.to * (1 - Math.pow(1 - p, 3)));
      c.el.textContent = c.fmt.replace("#", n.toLocaleString("en-US"));
    });
  }

  var states = Array.prototype.map.call(teasers, setup);

  // Lets a preview page park every teaser on one frame.
  window.siteTeasers = {
    seek: function (frac) { states.forEach(function (s) { s.running = false; seek(s, frac); }); }
  };

  if (reduce || !("IntersectionObserver" in window)) return;

  function play(s) {
    if (s.running) return;
    s.running = true;
    // start every visit from the top of the loop so the story reads in order
    s.anims.forEach(function (a) { a.currentTime = 0; a.play(); });
    if (s.counters.length) requestAnimationFrame(function tick() {
      if (!s.running) return;
      var t = s.anims[0].currentTime || 0;
      paint(s, (t % s.dur) / s.dur);
      requestAnimationFrame(tick);
    });
  }

  function stop(s) {
    if (!s.running) return;
    s.running = false;
    s.held = false;
    seek(s, num(s.svg, "poster", 0.9));
  }

  // Hovering or focusing a teaser freezes it on the current frame, so it can
  // be read (and so looping motion can always be paused); leaving resumes.
  function hold(s) {
    if (!s.running || s.held) return;
    s.held = true;
    s.anims.forEach(function (a) { a.pause(); });
  }

  function resume(s) {
    if (!s.held) return;
    s.held = false;
    if (s.running) s.anims.forEach(function (a) { a.play(); });
  }

  states.forEach(function (s) {
    var host = s.svg.closest("a") || s.svg;
    host.addEventListener("mouseenter", function () { hold(s); });
    host.addEventListener("mouseleave", function () { resume(s); });
    host.addEventListener("focusin", function () { hold(s); });
    host.addEventListener("focusout", function () { resume(s); });
  });

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      var s = states[Array.prototype.indexOf.call(teasers, e.target)];
      if (e.isIntersecting) play(s); else stop(s);
    });
  }, { threshold: 0.35 });

  teasers.forEach(function (t) { io.observe(t); });
})();
