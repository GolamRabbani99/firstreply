/* Firstreply assistant — self-contained chat + voice widget.
   Scripted knowledge base (no external calls, no cookies, no storage):
   answers initial queries, qualifies, routes to booking/email.
   Voice: speech-to-text via the browser's SpeechRecognition where available,
   optional spoken replies via speechSynthesis. Honest by design — it says
   it's an assistant, and hands anything complex to a human. */
(function () {
  'use strict';
  if (window.__frChat) return;
  window.__frChat = true;

  var BOOK = '/#book';
  var CAL = 'https://calendly.com/golamrabbani-com/lead-leak-audit';
  var MAIL = 'mailto:golam@firstreply.dev';
  var TEL = 'tel:+447535421734';

  /* ── knowledge base ─────────────────────────────────────────────── */
  var INTENTS = [
    { k: ['price', 'pricing', 'cost', 'fee', 'how much', 'charge', 'expensive'],
      a: 'Straight answer — our three packages:\n• Tracking Fix: £800–£1,200 one-off\n• Speed-to-Lead System: £1,500–£2,500 setup + £250/month\n• Full Growth Engine: £1,000–£2,000/month, rolling with 30 days’ notice.\nNo long contracts, ever.',
      c: [['See pricing details', '/#pricing'], ['Book a free call', BOOK]] },
    { k: ['book', 'call', 'appointment', 'meeting', 'audit', 'calendly', 'consultation', 'demo'],
      a: 'The free strategy call is 15 minutes, no obligation — we look at your ads, forms and inbox together and show you where enquiries leak.',
      c: [['Open the booking calendar', CAL], ['Go to the booking section', BOOK]] },
    { k: ['what do you do', 'services', 'help me', 'offer', 'automation', 'automate'],
      a: 'We’re an AI business automation & growth partner. In one line: we generate leads, answer every enquiry in under 60 seconds (human-approved), and automate the repetitive work — chatbots, voice agents, CRM, marketing automation, all on n8n.',
      c: [['Browse all services', '/services/'], ['How it works', '/#journey']] },
    { k: ['voice', 'phone', 'answering', 'receptionist', 'calls', 'missed call'],
      a: 'Our AI voice agents answer your business phone 24/7 — enquiries handled, bookings taken, and a summary sent to your WhatsApp. They introduce themselves as assistants and pass anything complex to you.',
      c: [['AI voice agents', '/services/ai-voice-agents'], ['Book a free call', BOOK]] },
    { k: ['chatbot', 'chat bot', 'whatsapp bot', 'messenger', 'instagram', 'dm'],
      a: 'We build chatbots for websites, WhatsApp, Messenger and Instagram — trained on your business, with human handover rules. (I’m the scripted junior version — the ones we build for clients are trained on their full business.)',
      c: [['AI chatbots service', '/services/ai-chatbots'], ['Book a free call', BOOK]] },
    { k: ['lead', 'ads', 'facebook', 'meta', 'google ads', 'marketing', 'campaign'],
      a: 'We don’t just automate leads — we generate them. Meta & Google ads run by a marketer with 5+ years hands-on, landing pages, funnels, and server-side tracking so every pound is traceable.',
      c: [['Lead generation service', '/services/lead-generation'], ['Why leads go cold (blog)', '/blog/why-your-facebook-leads-go-cold']] },
    { k: ['crm', 'pipeline', 'hubspot', 'follow up', 'follow-up'],
      a: 'CRM automation: every enquiry becomes a contact automatically, deals move themselves, follow-up triggers fire before leads go cold, and reports build themselves weekly.',
      c: [['CRM automation service', '/services/crm-automation']] },
    { k: ['secure', 'security', 'gdpr', 'data', 'privacy', 'safe'],
      a: 'GDPR-by-design is our thing — the founder’s MSc is in Computer Network & System Security. Data minimisation, human approval on every customer-facing message, and you own everything we build. This chat stores nothing and sends nothing off this page.',
      c: [['Security & compliance', '/#security'], ['Privacy policy', '/privacy']] },
    { k: ['industr', 'restaurant', 'cater', 'construction', 'builder', 'estate', 'dentist', 'clinic', 'recruit', 'education', 'school', 'tutor'],
      a: 'We build industry-specific systems for restaurants & catering, construction & trades, estate agents, dentists & clinics, education & training, and recruitment agencies.',
      c: [['See your industry', '/industries/']] },
    { k: ['who are you', 'about', 'founder', 'golam', 'company', 'where are you', 'location', 'london'],
      a: 'Firstreply is run by Golam Rabbani — ex-Digital Marketing Manager (5+ years on Meta ads) with an MSc in Computer Network & System Security. Based in London, working remotely with clients anywhere.',
      c: [['About us', '/about'], ['Our one real case study', '/case-studies']] },
    { k: ['case stud', 'proof', 'result', 'client', 'testimonial', 'review', 'diji'],
      a: 'Two kinds of proof, both real:\n• Firstreply case study: Diji Catering (London) — 4-hour replies down to 60 seconds, zero enquiries missed.\n• Founder’s ads track record: £22k+ managed spend, 5,500+ leads across ExploreX, London Pioneer Education and Radix Point, at £3.75–£5 per lead.\nNo invented testimonials, ever.',
      c: [['Read the case study', '/case-studies'], ['Watch the 60-sec simulation', '/#proof']] },
    { k: ['roi', 'calculator', 'worth', 'lose', 'losing', 'cost me'],
      a: 'Try the free ROI calculator — you enter your own enquiry numbers and it shows what slow replies cost you monthly. No email required, assumptions stated.',
      c: [['Open the ROI calculator', '/roi-calculator']] },
    { k: ['human', 'person', 'someone', 'speak to', 'talk to', 'real'],
      a: 'Absolutely — I’m only the doorman. Golam reads every message personally.',
      c: [['Book a call with Golam', CAL], ['Email him directly', MAIL]] },
    { k: ['email', 'contact', 'reach', 'message you'],
      a: 'You can email golam@firstreply.dev or call 07535 421734 — a human replies, usually within one working day. Or book the free 15-minute call.',
      c: [['Email us', MAIL], ['Call 07535 421734', TEL], ['Book a free call', BOOK]] },
    { k: ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'],
      a: 'Hello! I’m the Firstreply assistant — the scripted little sibling of the systems we build for clients. Ask me about services, pricing or booking, or tap a button below.',
      c: [['What do you do?', '@what do you do'], ['Pricing', '@pricing'], ['Book a free call', BOOK]] },
    { k: ['thank', 'cheers', 'great', 'perfect', 'ok'],
      a: 'You’re welcome! Anything else — pricing, services, or a free strategy call?',
      c: [['Book a free call', BOOK], ['Email a human', MAIL]] }
  ];
  var FALLBACK = {
    a: 'That one’s beyond my script — I’m an honest bot, so I won’t guess. A human can answer it properly:',
    c: [['Book a free 15-min call', CAL], ['Email golam@firstreply.dev', MAIL], ['Browse services', '/services/']]
  };

  function answer(text) {
    var t = ' ' + text.toLowerCase().trim() + ' ';
    for (var i = 0; i < INTENTS.length; i++) {
      for (var j = 0; j < INTENTS[i].k.length; j++) {
        if (t.indexOf(INTENTS[i].k[j]) !== -1) return INTENTS[i];
      }
    }
    return FALLBACK;
  }

  /* ── styles ─────────────────────────────────────────────────────── */
  var css = '' +
  '.frc-btn{position:fixed;right:1.1rem;bottom:1.1rem;z-index:70;width:60px;height:60px;border-radius:50%;border:0;cursor:pointer;background:#FFB224;box-shadow:0 8px 28px rgba(11,21,34,.35);display:flex;align-items:center;justify-content:center;transition:transform .15s}' +
  '.frc-btn:hover{transform:scale(1.06)}.frc-btn svg{width:30px;height:30px}' +
  '@media(max-width:767px){body.frc-has-sticky .frc-btn{bottom:5.2rem}}' +
  '.frc-panel{position:fixed;right:1.1rem;bottom:5.6rem;z-index:71;width:min(370px,calc(100vw - 2rem));max-height:min(560px,calc(100vh - 7rem));background:#fff;border:1px solid #E5E0D8;border-radius:16px;box-shadow:0 16px 48px rgba(11,21,34,.28);display:flex;flex-direction:column;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}' +
  '@media(max-width:767px){body.frc-has-sticky .frc-panel{bottom:9.6rem}}' +
  '.frc-head{background:#0B1522;color:#EAF0F6;padding:.9rem 1rem;display:flex;align-items:center;gap:.6rem}' +
  '.frc-head b{font-size:.95rem}.frc-head small{display:block;font-size:.72rem;color:#9FB0C0;font-weight:400}' +
  '.frc-x{margin-left:auto;background:none;border:0;color:#9FB0C0;font-size:1.4rem;cursor:pointer;min-width:44px;min-height:44px}' +
  '.frc-x:hover{color:#fff}' +
  '.frc-msgs{flex:1;overflow-y:auto;padding:1rem;display:flex;flex-direction:column;gap:.6rem;background:#FAF8F4}' +
  '.frc-m{max-width:88%;padding:.6rem .8rem;border-radius:12px;font-size:.88rem;line-height:1.5;white-space:pre-line}' +
  '.frc-bot{background:#fff;border:1px solid #E5E0D8;align-self:flex-start;border-bottom-left-radius:4px;color:#22303F}' +
  '.frc-user{background:#0B1522;color:#EAF0F6;align-self:flex-end;border-bottom-right-radius:4px}' +
  '.frc-chips{display:flex;flex-wrap:wrap;gap:.4rem;align-self:flex-start}' +
  '.frc-chip{border:1px solid #8A5A00;color:#8A5A00;background:#fff;border-radius:99px;padding:.45rem .8rem;font-size:.8rem;font-weight:600;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;min-height:36px}' +
  '.frc-chip:hover{background:#FFB224;border-color:#FFB224;color:#0B1522}' +
  '.frc-in{display:flex;gap:.4rem;padding:.7rem;border-top:1px solid #E5E0D8;background:#fff}' +
  '.frc-in input{flex:1;font:inherit;font-size:.9rem;padding:.6rem .8rem;border:1px solid #E5E0D8;border-radius:10px;min-height:44px}' +
  '.frc-in input:focus{outline:3px solid #FFB224;outline-offset:1px}' +
  '.frc-ib{border:0;border-radius:10px;min-width:44px;min-height:44px;cursor:pointer;display:flex;align-items:center;justify-content:center;background:#0B1522;color:#FFB224}' +
  '.frc-ib.frc-mic{background:#F2EEE7;color:#51606F}.frc-ib.frc-mic.on{background:#D9534F;color:#fff}' +
  '.frc-note{font-size:.68rem;color:#51606F;text-align:center;padding:.35rem .7rem .6rem;background:#fff}' +
  '@media (prefers-reduced-motion:no-preference){.frc-panel{animation:frcin .22s ease}@keyframes frcin{from{opacity:0;transform:translateY(12px)}to{opacity:1}}}';
  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  /* ── DOM ────────────────────────────────────────────────────────── */
  var robot = '<svg viewBox="0 0 24 24" fill="none" stroke="#0B1522" stroke-width="1.9" aria-hidden="true"><path d="M12 3v3M8 21h8"/><rect x="4" y="6" width="16" height="11" rx="3"/><circle cx="9" cy="11.5" r="1.2" fill="#0B1522" stroke="none"/><circle cx="15" cy="11.5" r="1.2" fill="#0B1522" stroke="none"/><path d="M9.5 14.2q2.5 1.6 5 0"/></svg>';
  var btn = document.createElement('button');
  btn.className = 'frc-btn'; btn.type = 'button';
  btn.setAttribute('aria-label', 'Open the Firstreply assistant — ask about services, pricing or booking');
  btn.innerHTML = robot;
  document.body.appendChild(btn);
  if (document.querySelector('.sticky-cta')) document.body.classList.add('frc-has-sticky');

  var panel = null, msgs = null, input = null, recog = null, speaking = false;

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  function say(text) {
    if (!speaking || !('speechSynthesis' in window)) return;
    try {
      var u = new SpeechSynthesisUtterance(text.replace(/•/g, '.'));
      u.lang = 'en-GB'; u.rate = 1.04;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    } catch (e) { /* voice is a bonus, never an error */ }
  }

  function addBot(text, chips) {
    var m = el('div', 'frc-m frc-bot'); m.textContent = text;
    msgs.appendChild(m);
    if (chips && chips.length) {
      var row = el('div', 'frc-chips');
      chips.forEach(function (c) {
        var label = c[0], target = c[1];
        var chip;
        if (target.charAt(0) === '@') {
          chip = el('button', 'frc-chip'); chip.type = 'button'; chip.textContent = label;
          chip.addEventListener('click', function () { send(target.slice(1)); });
        } else {
          chip = el('a', 'frc-chip'); chip.textContent = label; chip.href = target;
          if (target.indexOf('http') === 0 && target.indexOf('firstreply.dev') === -1) chip.rel = 'noopener';
        }
        row.appendChild(chip);
      });
      msgs.appendChild(row);
    }
    msgs.scrollTop = msgs.scrollHeight;
    say(text);
  }

  function send(text) {
    text = (text || '').trim();
    if (!text) return;
    var m = el('div', 'frc-m frc-user'); m.textContent = text;
    msgs.appendChild(m);
    msgs.scrollTop = msgs.scrollHeight;
    input.value = '';
    var res = answer(text);
    setTimeout(function () { addBot(res.a, res.c); }, 350);
  }

  function open() {
    if (typeof window.frTrack === 'function') window.frTrack('chat_opened', { page: location.pathname });
    if (panel) { panel.hidden = false; input.focus(); return; }
    panel = el('div', 'frc-panel');
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Firstreply assistant chat');

    var head = el('div', 'frc-head',
      robot.replace('#0B1522', '#FFB224').replace(/#0B1522/g, '#FFB224') +
      '<div><b>Firstreply assistant</b><small>instant scripted answers · a human reads anything you leave</small></div>');
    var x = el('button', 'frc-x', '×'); x.type = 'button';
    x.setAttribute('aria-label', 'Close chat');
    x.addEventListener('click', function () { panel.hidden = true; btn.focus(); });
    head.appendChild(x);
    panel.appendChild(head);

    msgs = el('div', 'frc-msgs');
    msgs.setAttribute('aria-live', 'polite');
    panel.appendChild(msgs);

    var inrow = el('div', 'frc-in');
    input = document.createElement('input');
    input.type = 'text'; input.maxLength = 300;
    input.placeholder = 'Ask about services, pricing, booking…';
    input.setAttribute('aria-label', 'Type your question');
    input.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') send(input.value); });
    inrow.appendChild(input);

    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SR) {
      var mic = el('button', 'frc-ib frc-mic',
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v1a7 7 0 0 0 14 0v-1M12 18v4"/></svg>');
      mic.type = 'button';
      mic.setAttribute('aria-label', 'Speak your question instead of typing');
      mic.title = 'Voice input — try the AI voice demo';
      mic.addEventListener('click', function () {
        if (recog) { recog.stop(); return; }
        recog = new SR();
        recog.lang = 'en-GB'; recog.interimResults = false;
        mic.classList.add('on');
        speaking = true; // voice question earns a spoken answer
        recog.onresult = function (ev) { send(ev.results[0][0].transcript); };
        recog.onend = function () { mic.classList.remove('on'); recog = null; };
        recog.onerror = function () { mic.classList.remove('on'); recog = null; };
        try { recog.start(); } catch (e) { mic.classList.remove('on'); recog = null; }
      });
      inrow.appendChild(mic);
    }

    var sendB = el('button', 'frc-ib',
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/></svg>');
    sendB.type = 'button';
    sendB.setAttribute('aria-label', 'Send message');
    sendB.addEventListener('click', function () { send(input.value); });
    inrow.appendChild(sendB);
    panel.appendChild(inrow);

    panel.appendChild(el('div', 'frc-note',
      'Scripted assistant · nothing you type is stored or sent anywhere' + (SR ? ' · 🎤 tap the mic to try voice' : '')));

    document.body.appendChild(panel);
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape' && panel && !panel.hidden) { panel.hidden = true; btn.focus(); }
    });

    addBot('Hi! I’m the Firstreply assistant — a small scripted example of what we build for clients (theirs are trained on their whole business). What can I help with?',
      [['What do you do?', '@what do you do'], ['Pricing', '@pricing'], ['Book a free call', BOOK], ['Talk to a human', '@human']]);
    input.focus();
  }

  btn.addEventListener('click', function () {
    if (panel && !panel.hidden) { panel.hidden = true; return; }
    open();
  });
})();
