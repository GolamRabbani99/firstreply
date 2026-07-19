/* Firstreply conversion tracking — vendor-neutral, cookieless, privacy-safe.
   Sends named events to whatever analytics is enabled (Vercel Web Analytics
   `window.va`, or Plausible `window.plausible`) and no-ops if neither is
   present. Stores nothing, sets no cookies. Auto-instruments the funnel:
   book clicks → calendar opens → BOOKINGS (via Calendly postMessage) →
   chat opens, ROI use, email clicks. This is how you see which pages
   actually produce clients, not just visits. */
(function () {
  'use strict';

  // Fire an event into every analytics tool that happens to be loaded.
  function track(name, props) {
    try {
      if (typeof window.va === 'function') window.va('event', Object.assign({ name: name }, props || {}));
      if (typeof window.plausible === 'function') window.plausible(name, props ? { props: props } : undefined);
    } catch (e) { /* analytics must never break the page */ }
  }
  window.frTrack = track; // exposed so other scripts (chat, ROI) can call it

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    // Which page is this? (for per-page conversion attribution)
    var page = location.pathname.replace(/\/$/, '') || '/';

    // 1. Every "book"/CTA click — the intent signal
    document.querySelectorAll('a[href="#book"], a[href="/#book"], a[href*="calendly.com"]').forEach(function (a) {
      a.addEventListener('click', function () {
        var toCal = a.href.indexOf('calendly.com') !== -1;
        track(toCal ? 'calendar_opened' : 'book_cta_click', { page: page });
      });
    });

    // 2. "Load booking calendar" button (homepage embed)
    var loadCal = document.getElementById('loadCal');
    if (loadCal) loadCal.addEventListener('click', function () { track('calendar_opened', { page: page, via: 'embed' }); });

    // 3. Email clicks
    document.querySelectorAll('a[href^="mailto:"]').forEach(function (a) {
      a.addEventListener('click', function () { track('email_click', { page: page }); });
    });

    // 4. Contact-form submit (homepage)
    var form = document.getElementById('leadForm');
    if (form) form.addEventListener('submit', function () { track('contact_form_submit', { page: page }); });

    // 5. ROI calculator engagement (fires once per visit)
    if (document.getElementById('roiForm')) {
      var roiFired = false;
      document.querySelectorAll('#roiForm input').forEach(function (i) {
        i.addEventListener('input', function () {
          if (!roiFired) { roiFired = true; track('roi_calculator_used', { page: page }); }
        });
      });
    }

    // 6. THE conversion: an actual booking. Calendly posts a message to the
    //    parent window when someone completes a booking in the embed.
    window.addEventListener('message', function (e) {
      if (e.origin && e.origin.indexOf('calendly.com') === -1) return;
      var d = e.data;
      if (d && typeof d.event === 'string' && d.event.indexOf('calendly.') === 0) {
        if (d.event === 'calendly.event_scheduled') {
          track('booking_completed', { page: page }); // <- the money event
        } else if (d.event === 'calendly.date_and_time_selected') {
          track('booking_slot_selected', { page: page });
        }
      }
    });
  });
})();
