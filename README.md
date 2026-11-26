# stratacyber.com.br

Static site for Strata Cyber, a cyber risk consultancy: risk assessment, control implementation and
security and privacy program management on NIST CSF 2.0, ISO/IEC 27001, ISO/IEC 27701 and the NIST Privacy Framework.
English at `/`, Portuguese at `/pt/`. URLs are English in both languages.
The only interactive element is the Calendly scheduler; articles are Markdown files in this repo.
No database, no CMS, no logins: what is in `main` is what is live.

- **Writing articles:** see [WRITING.md](WRITING.md).
- **Settings** (Calendly link, email, LinkedIn): [site.toml](site.toml).
- **Home page copy:** [templates/home.en.html](templates/home.en.html) and [templates/home.pt.html](templates/home.pt.html).
- **Styles:** [static/css/site.css](static/css/site.css), built on the Brand Guidelines v1.0 tokens.

## Layout

```
build.py                  the generator (Python 3.11+, one dependency: Markdown)
site.toml                 settings
content/articles/en/*.md  English articles (TOML front matter between +++ lines)
content/articles/pt/*.md  Portuguese articles; same file name = translation
templates/                home page and "latest articles" block, per language
static/                   CSS, the Calendly loader, fonts, logos, favicons, OG images
tools/check_site.py       checks dist/: links, anchors, alt text, meta tags, hreflang, sitemap
tools/brand_assets.py     regenerates static/fonts, static/brand, favicons and og-*.png from the brand kit
.github/workflows/        check.yml on pull requests; deploy.yml builds and deploys to GitHub Pages
.github/dependabot.yml    weekly update PRs for pip and GitHub Actions
```

## Run locally

```
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python build.py serve
```

Then open http://localhost:8000. Edits to content, templates, static files and `site.toml` rebuild automatically;
changes to `build.py` need a restart. `python build.py` alone writes the site to `dist/`.

## Deploy (GitHub Pages)

1. Push this folder to a GitHub repository, branch `main`.
2. Repository **Settings → Pages → Source: GitHub Actions**.
3. **Settings → Pages → Custom domain:** `stratacyber.com.br`, then tick **Enforce HTTPS**.
4. At the DNS provider: `A` records for the apex to GitHub Pages
   (`185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`) and a `CNAME` for `www` to `<user>.github.io`.

The workflow builds on every push to `main` and once a day at 06:00 BRT, which is what makes
future-dated articles go live on their own. GitHub pauses scheduled workflows in public repositories
after 60 days without activity; any push turns it back on.

Any static host works the same way (Cloudflare Pages, Netlify): build command `pip install -r requirements.txt && python build.py`, output directory `dist`.

### Live setup (since 2026-11-26)

- Repository: `strata-cyber/stratacyber-site` (public; Pages on private repositories needs a paid plan).
  Commits use the repository-only identity `Strata Cyber <strata-cyber@users.noreply.github.com>`.
- Domain verified for GitHub Pages on the `strata-cyber` account, so no other account can claim it.
- DNS is hosted by Registro.br (`d.sec.dns.br`, `f.sec.dns.br`) with DNSSEC on. Records in the zone:

  | Name | Type | Value | Purpose |
  |---|---|---|---|
  | `@` | A ×4 | `185.199.108.153` … `185.199.111.153` | GitHub Pages |
  | `www` | CNAME | `strata-cyber.github.io` | GitHub Pages |
  | `@` | MX | `1 smtp.google.com` | Google Workspace mail |
  | `@` | TXT | `v=spf1 include:_spf.google.com ~all` | SPF: only Google sends as the domain |
  | `google._domainkey` | TXT | `v=DKIM1; k=rsa; p=…` | DKIM (Google Workspace) |
  | `_dmarc` | TXT | `v=DMARC1; p=quarantine; rua=mailto:…; adkim=s; aspf=s` | DMARC; move to `p=reject` once reports are clean |
  | `_smtp._tls` | TXT | `v=TLSRPTv1; rua=mailto:…` | TLS delivery reports |
  | `_github-pages-challenge-strata-cyber` | TXT | (GitHub code) | Pages domain verification |
  | `@` | TXT, `isynu7s3mr66` CNAME | `google-site-verification…` | Google domain verification |

  A new service that sends email as `@stratacyber.com.br` must be added to the single SPF record first.
- `static/brand/strata-cyber-logo-charcoal.png` is the public copy of the logo that the brand kit's Google Docs and
  Slides builders embed (those editors only take images from a public URL).

## Rebuilding brand assets

Only needed if the brand kit changes:

```
.venv\Scripts\python -m pip install -r requirements-tools.txt
.venv\Scripts\python tools\brand_assets.py "C:\path\to\Strata Cyber Brand Kit"
```

## Privacy and security notes

- Fonts, logos and styles are self-hosted. No analytics, no cookies from this site.
- Calendly is the only third party. Its script loads only when the visitor scrolls near the booking section, and the page says so.
- A Content-Security-Policy meta tag limits scripts and frames to this origin and Calendly.
- GitHub Pages cannot send custom HTTP headers, so `frame-ancestors`/clickjacking protection and HSTS
  are not set. If that matters, put Cloudflare in front and add them there.
- The build refuses to publish any article labelled TLP other than CLEAR.
