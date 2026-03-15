// LEPA Tracker — embed via:
// <script async src="https://your-backend/tracker.js?key=YOUR_API_KEY"></script>
(function () {
  'use strict';

  // ── 1. Self-identify & extract API key ────────────────────────────────
  var _s = (document.currentScript && document.currentScript.tagName === 'SCRIPT')
    ? document.currentScript
    : document.querySelector('script[src*="tracker.js"]');
  if (!_s) return;
  var _key = new URL(_s.src).searchParams.get('key') || '';
  if (!_key) return;

  // ── 2. Bot detection ──────────────────────────────────────────────────
  var _ua = (navigator.userAgent || '').toLowerCase();
  if (/bot|crawl|spider|headless|phantom|selenium/.test(_ua) || navigator.webdriver) return;

  // ── 3. Visitor / session IDs ──────────────────────────────────────────
  function _uuid() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, function(c) {
      return (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16);
    });
  }
  var _vid = (function() {
    try { return localStorage.getItem('_lepa_vid') || (function(id){ localStorage.setItem('_lepa_vid', id); return id; }(_uuid())); }
    catch(e) { return _uuid(); }
  }());
  var _sid = (function() {
    try { return sessionStorage.getItem('_lepa_sid') || (function(id){ sessionStorage.setItem('_lepa_sid', id); return id; }(_uuid())); }
    catch(e) { return _uuid(); }
  }());

  // ── 4. Time-on-page (active only) ────────────────────────────────────
  var _active = 0, _lastVisible = Date.now();
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { _active += Date.now() - _lastVisible; }
    else { _lastVisible = Date.now(); }
  });

  // ── 5. Batch queue + beacon flush ────────────────────────────────────
  var _ENDPOINT = (new URL(_s.src).searchParams.get('endpoint') || 'http://localhost:8000') + '/track';
  var _q = [], _timer = null;

  function _push(e) {
    _q.push(e);
    if (!_timer) _timer = setTimeout(_flush, 4000);
  }

  function _flush() {
    if (!_q.length) return;
    clearTimeout(_timer); _timer = null;
    // Include time elapsed since last visible snapshot
    var currentActive = _active + (document.hidden ? 0 : (Date.now() - _lastVisible));
    var body = JSON.stringify({ key: _key, vid: _vid, sid: _sid, events: _q.splice(0), active_ms: currentActive });
    var blob = new Blob([body], { type: 'text/plain' });
    if (navigator.sendBeacon) {
      navigator.sendBeacon(_ENDPOINT, blob);
    } else {
      fetch(_ENDPOINT, { method: 'POST', body: blob, keepalive: true, mode: 'no-cors' }).catch(function(){});
    }
  }

  document.addEventListener('visibilitychange', function () { if (document.hidden) _flush(); });
  window.addEventListener('pagehide', _flush);

  // ── 6. Heartbeat — update active time every 30s for long sessions ────
  setInterval(function () {
    if (!document.hidden) {
      var currentActive = _active + (Date.now() - _lastVisible);
      var body = JSON.stringify({ key: _key, vid: _vid, sid: _sid, events: [], active_ms: currentActive });
      var blob = new Blob([body], { type: 'text/plain' });
      if (navigator.sendBeacon) navigator.sendBeacon(_ENDPOINT, blob);
    }
  }, 30000);

  // ── 7. SPA page tracking ──────────────────────────────────────────────
  var _lastUrl = location.href;

  function _trackPage() {
    var url = location.href;
    if (url === _lastUrl) return;
    _push({ type: 'pageview', url: url, ref: _lastUrl, active_ms: _active });
    _lastUrl = url; _active = 0; _lastVisible = Date.now();
  }

  ['pushState', 'replaceState'].forEach(function (fn) {
    var orig = history[fn];
    history[fn] = function () { orig.apply(this, arguments); _trackPage(); };
  });
  window.addEventListener('popstate', _trackPage);
  window.addEventListener('hashchange', _trackPage);

  // Initial pageview
  _push({ type: 'pageview', url: _lastUrl, ref: document.referrer });
}());
