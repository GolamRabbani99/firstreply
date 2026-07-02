# Firstreply — deployment checklist

Files: `index.html` (the site), `privacy.html` (linked from footer + form). No build step — upload both files to any static host.

## 1. Replace every placeholder (search the files for `[` and `YOUR-`)

| Placeholder | Where | Replace with |
|---|---|---|
| `https://YOUR-N8N-DOMAIN.example` | CSP meta tag **and** `CONFIG.WEBHOOK_URL` in the script (index.html) | Your n8n instance origin + webhook path. **Both must match** or the browser blocks the form (that's the CSP doing its job). |
| `[CALENDLY_URL]` | `CONFIG.CALENDLY_URL` in script + "open in new tab" link | Your Calendly event link. Using Cal.com instead? Also change `frame-src https://calendly.com` → `https://cal.com` in the CSP. |
| `44XXXXXXXXXX` | 3 WhatsApp links (final CTA, footer, sticky bar) | Your number in international format, no `+`, e.g. `447700900123`. |
| `[X]` and `[MONTHS]` | Case study metrics | Real Diji Catering numbers. **Do not launch with placeholders visible.** |
| `[LOOM_URL]`, `[GITHUB_URL]` | Proof section + footer | Your Loom demo and GitHub links. |
| `https://firstreply.dev` | Canonical, og:url, JSON-LD | Your real domain. |
| `[CONTACT_EMAIL]`, `[DATE]` | privacy.html | Your contact email; today's date. |

## 2. Connect the form to n8n (click-by-click)

1. In n8n: **Add workflow → Webhook node** → Method `POST`, Path `firstreply-lead`, Respond `Immediately` (or use a "Respond to Webhook" node returning status 200).
2. The site sends JSON: `{ name, business, email, message, source, ts }`.
3. Add next nodes as you like: WhatsApp/Telegram alert to you, append to Google Sheet, AI draft reply, etc.
4. Click **Activate** (production URL, not the test URL).
5. Paste the **Production URL** into `CONFIG.WEBHOOK_URL` and put its origin (e.g. `https://n8n.yourdomain.com`) into the CSP `connect-src`.
6. In n8n, restrict the webhook: check the `source` field equals `firstreply-site`, rate-limit if your instance is public, and never echo submitted data back in the response.
7. Test: submit the form → you should see "Sent ✓". Check the n8n execution log.

## 3. Security headers — handled by Vercel

The site deploys on **Vercel** (GitHub repo `GolamRabbani99/firstreply`, connected via the Vercel dashboard). `vercel.json` in the repo root sets every security header automatically on each deploy: CSP (with `frame-ancestors 'none'`), X-Content-Type-Options, Referrer-Policy, Permissions-Policy, X-Frame-Options and HSTS. Nothing to configure by hand.

**Important:** when you set your real n8n domain (step 1), update it in **both** `index.html` (CSP meta + `CONFIG.WEBHOOK_URL`) **and** `vercel.json` (`connect-src`) — then push, and Vercel redeploys automatically.

To update the live site after any edit: commit and push to `main`. Vercel rebuilds in under a minute.

## 4. Lighthouse test

1. Open the deployed site in Chrome → DevTools (F12) → **Lighthouse** tab.
2. Run **Mobile**, all categories, in an incognito window (extensions skew scores).
3. Expect 95+ across the board: no external fonts, no third-party scripts on load, explicit sizes on media, single ~35 KB page. If Performance dips, it's almost always the host's TTFB — Cloudflare in front fixes that too.

## 5. Optional: cookieless analytics

A commented Plausible slot is at the bottom of `index.html` with instructions (uncomment + add plausible.io to the CSP). Plausible is cookieless, so no consent banner is required under UK GDPR/PECR.
