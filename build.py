#!/usr/bin/env python3
"""Strata Cyber website builder.

Turns content/articles/{en,pt}/*.md + templates/ + static/ into a static site in dist/.
No database, no admin panel: publishing an article means committing a
Markdown file. See WRITING.md.

    python build.py            build dist/
    python build.py serve      build, serve on http://localhost:8000, rebuild on change
    python build.py --drafts   also build drafts and future-dated articles (local preview)
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import html
import http.server
import math
import re
import shutil
import sys
import threading
import time
import tomllib
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import markdown
from markdown.extensions.toc import slugify_unicode

ROOT = Path(__file__).resolve().parent
ARTICLES_DIR = ROOT / "content" / "articles"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DIST = ROOT / "dist"
BRT = timezone(timedelta(hours=-3))  # Brazil has had no DST since 2019.

SEVERITIES = ("critical", "high", "medium", "low", "info")
TLPS = ("RED", "AMBER+STRICT", "AMBER", "GREEN", "CLEAR")

# English is the default language and lives at the site root; Portuguese lives under /pt/.
# URL segments and #anchors are English in both languages; only the visible text changes.
DEFAULT_LANG = "en"
L10N = {
    "en": {
        "html_lang": "en", "og_locale": "en_US", "prefix": "",
        "months": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(),
        "skip": "Skip to content", "nav_label": "Main",
        "nav_services": "Services", "nav_frameworks": "Frameworks", "nav_articles": "Articles", "nav_book": "Book a call",
        "switch": "PT", "switch_title": "Portuguese version", "switch_lang": "pt",
        "tagline": "Cyber risk consultancy: security and privacy programs on NIST and ISO frameworks.",
        "home_title": "Strata Cyber · Cyber risk consultancy",
        "home_description": "Cyber risk assessment, control implementation and security and privacy program management "
                            "on NIST CSF 2.0, ISO/IEC 27001, ISO/IEC 27701 and the NIST Privacy Framework, for LGPD and GDPR.",
        "articles_title": "Articles",
        "articles_lede": "Notes on cyber risk, security and privacy programs, and the threats behind them.",
        "articles_empty": "No articles published yet.",
        "all_articles": "All articles",
        "default_kind": "Article",
        "min_read": "min read",
        "by": "By", "published": "Published", "updated": "Updated", "reading": "Reading",
        "toc": "In this article", "other_lang": "Read in Portuguese",
        "cta_eyebrow": "Next step",
        "cta_title": "Need to apply this to your environment?",
        "cta_body": "Tell us the context and leave the call with a defined next step.",
        "cta_button": "Book a call",
        "location": "Aracaju, Brazil",
        "feed": "RSS feed", "rights": "All rights reserved.",
        "severity": {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low", "info": "Info"},
        "nf_title": "Page not found",
        "nf_body": "This address does not exist or has moved.",
        "nf_home": "Back to the homepage",
    },
    "pt": {
        "html_lang": "pt-BR", "og_locale": "pt_BR", "prefix": "/pt",
        "months": "jan fev mar abr mai jun jul ago set out nov dez".split(),
        "skip": "Pular para o conteúdo", "nav_label": "Principal",
        "nav_services": "Serviços", "nav_frameworks": "Frameworks", "nav_articles": "Artigos", "nav_book": "Agendar",
        "switch": "EN", "switch_title": "Versão em inglês", "switch_lang": "en",
        "tagline": "Consultoria em risco cibernético: programas de segurança e privacidade sobre frameworks NIST e ISO.",
        "home_title": "Strata Cyber · Consultoria em risco cibernético",
        "home_description": "Avaliação de risco cibernético, implementação de controles e gestão de programas de segurança e "
                            "privacidade sobre NIST CSF 2.0, ISO/IEC 27001, ISO/IEC 27701 e NIST Privacy Framework, para LGPD e GDPR.",
        "articles_title": "Artigos",
        "articles_lede": "Notas sobre risco cibernético, programas de segurança e privacidade, e as ameaças por trás deles.",
        "articles_empty": "Nenhum artigo publicado ainda.",
        "all_articles": "Todos os artigos",
        "default_kind": "Artigo",
        "min_read": "min de leitura",
        "by": "Por", "published": "Publicado", "updated": "Atualizado", "reading": "Leitura",
        "toc": "Neste artigo", "other_lang": "Ler em inglês",
        "cta_eyebrow": "Próximo passo",
        "cta_title": "Precisa aplicar isso no seu ambiente?",
        "cta_body": "Conte o contexto e saia da conversa com um próximo passo definido.",
        "cta_button": "Agendar uma conversa",
        "location": "Aracaju, Brasil",
        "feed": "Feed RSS", "rights": "Todos os direitos reservados.",
        "severity": {"critical": "Crítico", "high": "Alto", "medium": "Médio", "low": "Baixo", "info": "Info"},
    },
}


class BuildError(Exception):
    pass


# --------------------------------------------------------------------------- content

@dataclass
class Article:
    source: Path
    slug: str
    lang: str
    title: str
    summary: str
    date: date
    body_md: str
    kind: str = ""
    author: str = ""
    tlp: str = ""
    severity: str = ""
    updated: date | None = None
    draft: bool = False
    body_html: str = ""
    toc: list = field(default_factory=list)
    words: int = 0
    other: "Article | None" = None

    @property
    def url(self) -> str:
        return f"{L10N[self.lang]['prefix']}/articles/{self.slug}/"

    @property
    def minutes(self) -> int:
        return max(1, math.ceil(self.words / 220))


FRONT_MATTER = re.compile(r"\A\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)\Z", re.S)


SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FIELDS = {"title", "summary", "date", "kind", "author", "tlp", "severity", "updated", "draft"}


def load_article(path: Path, lang: str) -> Article:
    name = f"{lang}/{path.name}"
    if not SLUG.match(path.stem):
        raise BuildError(f"{name}: file name becomes the URL; use lowercase letters, digits and hyphens only")
    text = path.read_text("utf-8").replace("\r\n", "\n")
    m = FRONT_MATTER.match(text)
    if not m:
        raise BuildError(f"{name}: missing +++ front matter +++ block (see WRITING.md)")
    try:
        meta = tomllib.loads(m.group(1))
    except tomllib.TOMLDecodeError as err:
        raise BuildError(f"{name}: front matter is not valid TOML: {err}") from None

    unknown = set(meta) - FIELDS
    if unknown:
        raise BuildError(f"{name}: unknown front matter key(s): {', '.join(sorted(unknown))}")
    for key in ("title", "summary", "date"):
        if key not in meta:
            raise BuildError(f"{name}: front matter needs `{key}`")
    for key in ("title", "summary", "kind", "author", "tlp", "severity"):
        if key in meta and not isinstance(meta[key], str):
            raise BuildError(f'{name}: {key} must be text in quotes, e.g. {key} = "..."')
    for key in ("title", "summary"):
        if not meta[key].strip():
            raise BuildError(f"{name}: {key} is empty")
    for key in ("date", "updated"):
        if key in meta and not isinstance(meta[key], date):
            raise BuildError(f"{name}: {key} must be a TOML date, e.g. {key} = 2026-11-26 (no quotes)")
    if "draft" in meta and not isinstance(meta["draft"], bool):
        raise BuildError(f"{name}: draft must be true or false (no quotes)")
    sev = meta.get("severity", "").strip().lower()
    if sev and sev not in SEVERITIES:
        raise BuildError(f"{name}: severity must be one of {', '.join(SEVERITIES)}")
    tlp = re.sub(r"\s+", "", meta.get("tlp", "")).upper().removeprefix("TLP:")
    if tlp and tlp not in TLPS:
        raise BuildError(f"{name}: tlp must be one of {', '.join(TLPS)}")
    if tlp and tlp != "CLEAR":
        # A public website is TLP:CLEAR by definition; publishing anything else would break the label.
        raise BuildError(f"{name}: TLP:{tlp} content cannot be published on a public site (only TLP:CLEAR)")

    d = meta["date"]
    d = d.date() if isinstance(d, datetime) else d
    upd = meta.get("updated")
    upd = upd.date() if isinstance(upd, datetime) else upd
    if upd and upd < d:
        raise BuildError(f"{name}: updated ({upd}) is earlier than date ({d})")
    return Article(
        source=path, slug=path.stem, lang=lang, title=meta["title"].strip(),
        summary=meta["summary"].strip(), date=d,
        body_md=m.group(2), kind=meta.get("kind", "").strip(), author=meta.get("author", "").strip(),
        tlp=tlp, severity=sev, updated=upd, draft=meta.get("draft", False),
    )


def render_markdown(a: Article) -> None:
    md = markdown.Markdown(
        extensions=["extra", "sane_lists", "smarty", "admonition", "toc"],
        extension_configs={"toc": {"toc_depth": "2", "slugify": slugify_unicode}},
        output_format="html",
    )
    out = md.convert(a.body_md)
    for tag in re.findall(r"<img\b[^>]*>", out):
        alt = re.search(r'\balt="([^"]*)"', tag)
        if not alt or not alt.group(1).strip():
            raise BuildError(f"{a.lang}/{a.source.name}: image without a description: {tag} "
                             "(write ![Description](file.png); see WRITING.md)")
    out = out.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    out = re.sub(r"<img (?![^>]*loading=)", '<img loading="lazy" decoding="async" ', out)
    # `TLP:AMBER` written as inline code becomes a FIRST-standard TLP label.
    out = re.sub(r"<code>TLP:(RED|AMBER\+STRICT|AMBER|GREEN|CLEAR)</code>",
                 lambda m: f'<span class="tlp tlp-{m.group(1).split("+")[0].lower()}">TLP:{m.group(1)}</span>', out)
    a.body_html = out
    a.toc = [(t["id"], t["name"]) for t in md.toc_tokens]
    a.words = len(re.sub(r"<[^>]+>", " ", out).split())


def load_articles(include_drafts: bool) -> list[Article]:
    """content/articles/<lang>/<slug>.md. The same file name in en/ and pt/ = translations of each other."""
    today = datetime.now(BRT).date()
    stray = [p.name for p in ARTICLES_DIR.glob("*.md") if not p.name.startswith("_")]
    if stray:
        raise BuildError(f"content/articles/{stray[0]}: move it into content/articles/en/ or content/articles/pt/")
    articles, by_key = [], {}
    for lang in L10N:
        for path in sorted((ARTICLES_DIR / lang).glob("*.md")):
            if path.name.startswith("_"):
                continue
            a = load_article(path, lang)
            if not include_drafts and (a.draft or a.date > today):
                continue
            render_markdown(a)
            articles.append(a)
            by_key[(lang, a.slug)] = a
    # Link translations; an unpublished translation simply means no link yet.
    for a in articles:
        other_lang = L10N[a.lang]["switch_lang"]
        a.other = by_key.get((other_lang, a.slug))
    articles.sort(key=lambda a: (a.date, a.title), reverse=True)
    return articles


# --------------------------------------------------------------------------- helpers

e = functools.partial(html.escape, quote=True)


def fmt_date(d: date, lang: str) -> str:
    return f"{d.day:02d} {L10N[lang]['months'][d.month - 1]} {d.year}"


def render_template(name: str, **ctx: str) -> str:
    text = (TEMPLATES / name).read_text("utf-8")

    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in ctx:
            raise BuildError(f"templates/{name}: no value for {{{{ {key} }}}}")
        return ctx[key]

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", sub, text)


def labels(a: Article) -> str:
    out = []
    if a.tlp:
        out.append(f'<span class="tlp tlp-{a.tlp.split("+")[0].lower()}">TLP:{e(a.tlp)}</span>')
    if a.severity:
        out.append(f'<span class="sev sev-{a.severity}">{e(L10N[a.lang]["severity"][a.severity])}</span>')
    return f'<span class="labels">{"".join(out)}</span>' if out else ""


def article_list(items: list[Article], lang: str, heading: str = "h3") -> str:
    t = L10N[lang]
    rows = []
    for a in items:
        rows.append(f"""
      <li class="entry">
        <time class="entry-date" datetime="{a.date.isoformat()}">{fmt_date(a.date, lang)}</time>
        <div class="entry-body">
          <p class="eyebrow">{e(a.kind or t['default_kind'])}</p>
          <{heading} class="entry-title"><a href="{a.url}">{e(a.title)}</a></{heading}>
          <p class="entry-summary">{e(a.summary)}</p>
        </div>
        <div class="entry-meta">{labels(a)}<span class="mono-note">{a.minutes} {t['min_read']}</span></div>
      </li>""")
    return f'<ol class="entries" reversed>{"".join(rows)}\n    </ol>'


# --------------------------------------------------------------------------- page shell

class Site:
    def __init__(self, cfg: dict, articles: list[Article]):
        self.cfg = cfg
        self.base = cfg["url"].rstrip("/")
        self.articles = articles
        css = (STATIC / "css" / "site.css").read_bytes()
        self.css_v = hashlib.sha256(css).hexdigest()[:10]
        self.year = datetime.now(BRT).year

    def by_lang(self, lang: str) -> list[Article]:
        return [a for a in self.articles if a.lang == lang]

    def home_url(self, lang: str) -> str:
        return L10N[lang]["prefix"] + "/"

    def index_url(self, lang: str) -> str:
        return f"{L10N[lang]['prefix']}/articles/"

    def header(self, lang: str, alt_url: str) -> str:
        t = L10N[lang]
        h = self.home_url(lang)
        return f"""
<header class="masthead">
  <div class="wrap masthead-inner">
    <a class="masthead-logo" href="{h}" aria-label="Strata Cyber">
      <svg viewBox="0 0 1080.35 379.62" aria-hidden="true"><use href="/brand/sprite.svg#horizontal"/></svg>
    </a>
    <nav class="masthead-nav" aria-label="{t['nav_label']}">
      <a class="nav-anchor" href="{h}#services">{t['nav_services']}</a>
      <a class="nav-anchor" href="{h}#frameworks">{t['nav_frameworks']}</a>
      <a href="{self.index_url(lang)}">{t['nav_articles']}</a>
      <a class="nav-book" href="{h}#book">{t['nav_book']}</a>
      <a class="nav-lang" href="{alt_url}" hreflang="{L10N[t['switch_lang']]['html_lang']}" lang="{L10N[t['switch_lang']]['html_lang']}" title="{e(t['switch_title'])}">{t['switch']}</a>
    </nav>
  </div>
</header>"""

    def footer(self, lang: str) -> str:
        t = L10N[lang]
        email = self.cfg.get("email", "")
        linkedin = self.cfg.get("linkedin", "")
        contact = []
        if email:
            contact.append(f'<a href="mailto:{e(email)}">{e(email)}</a>')
        if linkedin:
            contact.append(f'<a href="{e(linkedin)}" rel="me">LinkedIn</a>')
        return f"""
<footer class="colophon">
  <div class="wrap colophon-inner">
    <div class="colophon-brand">
      <svg class="colophon-logo" viewBox="0 0 1080.35 379.62" role="img" aria-label="Strata Cyber"><use href="/brand/sprite.svg#horizontal"/></svg>
      <p>{t['tagline']}</p>
    </div>
    <ul class="colophon-list">
      <li>{t['location']}</li>
      {''.join(f'<li>{c}</li>' for c in contact)}
    </ul>
    <ul class="colophon-list">
      <li><a href="{self.index_url(lang)}">{t['nav_articles']}</a></li>
      <li><a href="{t['prefix']}/feed.xml">{t['feed']}</a></li>
      <li><a href="{self.home_url(t['switch_lang'])}" hreflang="{L10N[t['switch_lang']]['html_lang']}" lang="{L10N[t['switch_lang']]['html_lang']}">{t['switch_title']}</a></li>
    </ul>
    <p class="colophon-legal">© {self.year} Strata Cyber. {t['rights']}</p>
  </div>
</footer>"""

    def page(self, *, lang: str, path: str, title: str, description: str, main: str,
             alternates: dict[str, str] | None = None, og_type: str = "website",
             extra_head: str = "", scripts: str = "", noindex: bool = False) -> str:
        t = L10N[lang]
        alternates = alternates or {}
        other = t["switch_lang"]
        alt_url = alternates.get(other, self.home_url(other))
        hreflang = "".join(
            f'\n<link rel="alternate" hreflang="{L10N[l]["html_lang"]}" href="{self.base}{u}">'
            for l, u in sorted(alternates.items()))
        if alternates:
            hreflang += f'\n<link rel="alternate" hreflang="x-default" href="{self.base}{alternates.get(DEFAULT_LANG, path)}">'
        robots = '\n<meta name="robots" content="noindex">' if noindex else ""
        return f"""<!doctype html>
<html lang="{t['html_lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#15171A">{robots}
<link rel="canonical" href="{self.base}{path}">{hreflang}
<link rel="preload" href="/fonts/archivo-expanded-800.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/archivo-400.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/css/site.css?v={self.css_v}">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="alternate" type="application/atom+xml" title="Strata Cyber · {t['articles_title']}" href="{self.base}{t['prefix']}/feed.xml">
<meta property="og:site_name" content="Strata Cyber">
<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="{t['og_locale']}">
<meta property="og:locale:alternate" content="{L10N[other]['og_locale']}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{self.base}{path}">
<meta property="og:image" content="{self.base}/og-{lang}.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Strata Cyber">
<meta name="twitter:card" content="summary_large_image">{extra_head}
</head>
<body>
<a class="skip" href="#main">{t['skip']}</a>
{self.header(lang, alt_url)}
<main id="main">
{main}
</main>
{self.footer(lang)}{scripts}
</body>
</html>
"""


# Calendly is the only third party. Everything else is served from our own origin.
CSP = ("default-src 'self'; "
       "script-src 'self' https://assets.calendly.com; "
       "style-src 'self' https://assets.calendly.com; "
       "img-src 'self' data: https://assets.calendly.com; "
       "font-src 'self'; "
       "frame-src https://calendly.com; "
       "connect-src 'self' https://calendly.com; "
       "base-uri 'self'; form-action 'none'; object-src 'none'; upgrade-insecure-requests")
# GitHub Pages cannot send response headers, so frame-ancestors, HSTS, X-Content-Type-Options and
# Permissions-Policy are not possible here (browsers ignore frame-ancestors in a meta tag).


# --------------------------------------------------------------------------- pages

def calendly_url(cfg: dict) -> str:
    url = cfg.get("calendly_url", "").strip()
    sep = "&" if "?" in url else "?"
    # Brand colours on Calendly's own surface: Paper background, Ink text, Garnet actions.
    return f"{url}{sep}hide_gdpr_banner=1&background_color=ffffff&text_color=15171a&primary_color=9e1f32"


def build_home(site: Site, lang: str) -> str:
    t = L10N[lang]
    latest = site.by_lang(lang)[:3]
    if latest:
        latest_html = render_template(
            f"latest.{lang}.html", list=article_list(latest, lang), index=site.index_url(lang))
    else:
        latest_html = ""
    email = site.cfg.get("email", "")
    main = render_template(
        f"home.{lang}.html",
        latest=latest_html,
        calendly=e(calendly_url(site.cfg)),
        calendly_plain=e(site.cfg.get("calendly_url", "")),
        email=e(email),
        articles=site.index_url(lang),
    )
    if not email:
        main = re.sub(r'\s*<p class="book-alt">.*?</p>', "", main, flags=re.S)
    other = t["switch_lang"]
    return site.page(
        lang=lang, path=site.home_url(lang), title=t["home_title"], description=t["home_description"],
        main=main, alternates={lang: site.home_url(lang), other: site.home_url(other)},
        scripts='\n<script src="/js/calendly.js" defer></script>',
    )


def build_index(site: Site, lang: str) -> str:
    t = L10N[lang]
    items = site.by_lang(lang)
    groups, year = [], None
    for a in items:
        if a.date.year != year:
            year = a.date.year
            groups.append((year, []))
        groups[-1][1].append(a)
    if groups:
        body = "".join(
            f'\n  <section class="year" aria-labelledby="y{y}">\n    <h2 class="year-label" id="y{y}">{y}</h2>\n    {article_list(g, lang, "h3")}\n  </section>'
            for y, g in groups)
    else:
        body = f'<p class="empty">{t["articles_empty"]}</p>'
    main = f"""
<section class="cover cover-compact">
  <div class="wrap">
    <p class="eyebrow eyebrow-mark">Strata Cyber</p>
    <h1>{t['articles_title']}</h1>
    <p class="cover-lede">{t['articles_lede']}</p>
  </div>
</section>
<div class="wrap archive">{body}
</div>"""
    other = t["switch_lang"]
    return site.page(
        lang=lang, path=site.index_url(lang), title=f"{t['articles_title']} · Strata Cyber",
        description=t["articles_lede"], main=main,
        alternates={lang: site.index_url(lang), other: site.index_url(other)},
    )


def build_article(site: Site, a: Article) -> str:
    t = L10N[a.lang]
    meta_rows = []
    if a.author:
        meta_rows.append((t["by"], e(a.author)))
    meta_rows.append((t["published"], f'<time datetime="{a.date.isoformat()}">{fmt_date(a.date, a.lang)}</time>'))
    if a.updated:
        meta_rows.append((t["updated"], f'<time datetime="{a.updated.isoformat()}">{fmt_date(a.updated, a.lang)}</time>'))
    meta_rows.append((t["reading"], f"{a.minutes} {t['min_read']}"))
    meta = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in meta_rows)

    aside = [f'<dl class="article-meta">{meta}</dl>']
    if a.other:
        aside.append(f'<p class="article-translation"><a href="{a.other.url}" hreflang="{L10N[a.other.lang]["html_lang"]}" lang="{L10N[a.other.lang]["html_lang"]}">{t["other_lang"]} →</a></p>')
    if len(a.toc) >= 3:
        links = "".join(f'<li><a href="#{e(i)}">{n}</a></li>' for i, n in a.toc)
        aside.append(f'<nav class="article-toc" aria-label="{t["toc"]}"><p class="eyebrow">{t["toc"]}</p><ol>{links}</ol></nav>')

    main = f"""
<article>
  <header class="cover">
    <div class="wrap">
      <p class="crumbs"><a href="{site.index_url(a.lang)}">{t['articles_title']}</a> /</p>
      <p class="eyebrow eyebrow-mark">{e(a.kind or t['default_kind'])}</p>
      <h1>{e(a.title)}</h1>
      <p class="cover-lede">{e(a.summary)}</p>
      {labels(a)}
    </div>
  </header>
  <div class="wrap article-grid">
    <aside class="article-aside">{''.join(aside)}</aside>
    <div class="article-main">
    <div class="prose">
{a.body_html}
    </div>
    <aside class="next-move">
      <p class="eyebrow">{t['cta_eyebrow']}</p>
      <h2>{t['cta_title']}</h2>
      <p>{t['cta_body']}</p>
      <a class="button" href="{site.home_url(a.lang)}#book">{t['cta_button']} <span aria-hidden="true">→</span></a>
    </aside>
    <p class="back"><a href="{site.index_url(a.lang)}">← {t['all_articles']}</a></p>
    </div>
  </div>
</article>"""
    alternates = {a.lang: a.url}
    if a.other:
        alternates[a.other.lang] = a.other.url
    head = (f'\n<meta property="article:published_time" content="{a.date.isoformat()}">'
            + (f'\n<meta property="article:modified_time" content="{a.updated.isoformat()}">' if a.updated else "")
            + (f'\n<meta name="author" content="{e(a.author)}">' if a.author else ""))
    return site.page(
        lang=a.lang, path=a.url, title=f"{a.title} · Strata Cyber", description=a.summary, main=main,
        alternates=alternates if a.other else {}, og_type="article", extra_head=head,
    )


def build_404(site: Site) -> str:
    en = L10N["en"]
    main = f"""
<section class="cover cover-full">
  <div class="wrap">
    <p class="eyebrow eyebrow-mark">404</p>
    <h1>{en['nf_title']}.</h1>
    <p class="cover-lede">{en['nf_body']} <a href="/">{en['nf_home']} →</a></p>
  </div>
</section>"""
    return site.page(lang="en", path="/404.html", title="404 · Strata Cyber", description=en["nf_body"],
                     main=main, noindex=True)


def build_feed(site: Site, lang: str) -> str:
    t = L10N[lang]
    items = site.by_lang(lang)[:20]
    updated = max((a.updated or a.date for a in items), default=datetime.now(BRT).date())
    entries = []
    for a in items:
        u = site.base + a.url
        entries.append(f"""
  <entry>
    <title>{e(a.title)}</title>
    <link href="{u}"/>
    <id>{u}</id>
    <published>{a.date.isoformat()}T09:00:00-03:00</published>
    <updated>{(a.updated or a.date).isoformat()}T09:00:00-03:00</updated>
    {f'<author><name>{e(a.author)}</name></author>' if a.author else ''}
    <summary>{e(a.summary)}</summary>
    <content type="html" xml:base="{u}">{e(a.body_html)}</content>
  </entry>""")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="{t['html_lang']}">
  <title>Strata Cyber · {t['articles_title']}</title>
  <subtitle>{e(t['tagline'])}</subtitle>
  <link href="{site.base}{t['prefix']}/feed.xml" rel="self"/>
  <link href="{site.base}{site.index_url(lang)}"/>
  <id>{site.base}{t['prefix']}/feed.xml</id>
  <updated>{updated.isoformat()}T09:00:00-03:00</updated>
  <author><name>Strata Cyber</name></author>{''.join(entries)}
</feed>
"""


def build_sitemap(site: Site) -> str:
    urls = [u for lang in L10N for u in (site.home_url(lang), site.index_url(lang))]
    urls += [a.url for a in site.articles]
    lastmod = {a.url: (a.updated or a.date).isoformat() for a in site.articles}
    body = "".join(
        f"\n  <url><loc>{site.base}{u}</loc>{f'<lastmod>{lastmod[u]}</lastmod>' if u in lastmod else ''}</url>"
        for u in urls)
    return f'<?xml version="1.0" encoding="utf-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}\n</urlset>\n'


# --------------------------------------------------------------------------- build

def write(rel: str, text: str) -> None:
    path = DIST / rel.lstrip("/")
    if rel.endswith("/"):
        path = path / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, "utf-8")


ASSET_TYPES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".pdf"}


def copy_assets(src: Path, dest: Path) -> None:
    """Copy an article's image folder. Only plain image/PDF files: no symlinks (they could pull in files
    from outside the repo), no hidden files, nothing that could overwrite the article's index.html."""
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src)
        where = f"{src.relative_to(ROOT).as_posix()}/{rel.as_posix()}"
        if p.is_symlink():
            raise BuildError(f"{where}: symbolic links are not allowed in article folders")
        if any(part.startswith(".") for part in rel.parts) or p.is_dir():
            continue
        if p.suffix.lower() not in ASSET_TYPES:
            raise BuildError(f"{where}: only {', '.join(sorted(ASSET_TYPES))} files go in an article folder")
        if p.suffix.lower() == ".svg" and re.search(r"<script|\bon\w+\s*=|javascript:", p.read_text("utf-8", "replace"), re.I):
            # An SVG opened on its own runs its scripts on this origin; GitHub Pages sends no CSP for it.
            raise BuildError(f"{where}: SVG contains script or event handlers; export it without them")
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)


def build(include_drafts: bool = False) -> int:
    cfg = tomllib.loads((ROOT / "site.toml").read_text("utf-8"))
    if not cfg.get("calendly_url", "").startswith("https://calendly.com/"):
        raise BuildError("site.toml: calendly_url must be a https://calendly.com/... link")
    if cfg.get("linkedin") and not cfg["linkedin"].startswith("https://"):
        raise BuildError("site.toml: linkedin must be an https:// link (or empty)")
    if cfg.get("email") and not re.fullmatch(r"[^@\s\"<>]+@[^@\s\"<>]+\.[a-z]{2,}", cfg["email"]):
        raise BuildError("site.toml: email does not look like an email address")
    if "REPLACE" in cfg["calendly_url"]:
        print("warning: site.toml calendly_url is still the placeholder", file=sys.stderr)

    articles = load_articles(include_drafts)
    site = Site(cfg, articles)

    if DIST.exists():
        for child in DIST.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    DIST.mkdir(exist_ok=True)
    shutil.copytree(STATIC, DIST, dirs_exist_ok=True)

    for lang in L10N:
        write(site.home_url(lang), build_home(site, lang))
        write(site.index_url(lang), build_index(site, lang))
        write(f"{L10N[lang]['prefix']}/feed.xml", build_feed(site, lang))
    for a in articles:
        write(a.url, build_article(site, a))
        assets = a.source.with_suffix("")  # content/articles/<lang>/<slug>/ holds that article's images
        if assets.is_dir():
            copy_assets(assets, DIST / a.url.strip("/"))
    write("/404.html", build_404(site))
    write("/sitemap.xml", build_sitemap(site))
    write("/robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {site.base}/sitemap.xml\n")
    return len(articles)


def serve(port: int, include_drafts: bool) -> None:
    def snapshot() -> dict:
        files = [ROOT / "site.toml", *ARTICLES_DIR.rglob("*"), *TEMPLATES.rglob("*"), *STATIC.rglob("*")]
        return {p: p.stat().st_mtime for p in files if p.is_file()}

    def rebuild() -> None:
        try:
            n = build(include_drafts)
            print(f"built {n} article(s)  {time.strftime('%H:%M:%S')}")
        except BuildError as err:
            print(f"error: {err}", file=sys.stderr)

    rebuild()
    own_mtime = (ROOT / "build.py").stat().st_mtime

    def watch() -> None:
        last, warned = snapshot(), False
        while True:
            time.sleep(0.7)
            now = snapshot()
            if now != last:
                last = now
                rebuild()
            if not warned and (ROOT / "build.py").stat().st_mtime != own_mtime:
                warned = True
                print("build.py changed: restart `python build.py serve` to run the new code "
                      "(content changes still rebuild with the old code)", file=sys.stderr)

    threading.Thread(target=watch, daemon=True).start()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kw):
            super().__init__(*args, directory=str(DIST), **kw)

        def send_error(self, code, message=None, explain=None):
            if code == 404 and (DIST / "404.html").exists():
                body = (DIST / "404.html").read_bytes()
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().send_error(code, message, explain)

        def log_message(self, *args):
            pass

    print(f"serving http://localhost:{port}  (Ctrl+C to stop)")
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", nargs="?", choices=["build", "serve"], default="build")
    p.add_argument("--drafts", action="store_true", help="include drafts and future-dated articles")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args()
    try:
        if args.command == "serve":
            serve(args.port, args.drafts)
        else:
            n = build(args.drafts)
            print(f"built dist/ with {n} article(s)")
    except BuildError as err:
        sys.exit(f"error: {err}")


if __name__ == "__main__":
    main()
