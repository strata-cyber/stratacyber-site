# stratacyber.com.br

Source of the Strata Cyber website, a static site built by `build.py` from Markdown and deployed to GitHub Pages.
English at `/`, Portuguese at `/pt/`.

## Layout

```
build.py                  the generator (Python 3.11+, one dependency: Markdown)
site.toml                 settings
content/articles/en/*.md  English articles (TOML front matter between +++ lines)
content/articles/pt/*.md  Portuguese articles; same file name = translation
templates/                home page and "latest articles" block, per language
static/                   CSS, the Calendly loader, fonts, logos, favicons, OG images
tools/check_site.py       checks dist/: links, anchors, alt text, meta tags, hreflang, sitemap
tools/brand_assets.py     regenerates fonts, logos, favicons and OG images from the brand kit
.github/                  pull-request check, Pages deploy, Dependabot
```

## Run locally

```
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python build.py serve
```

Then open http://localhost:8000. `python build.py` alone writes the site to `dist/`.

## Privacy

Fonts, logos and styles are self-hosted. No analytics and no cookies. Calendly is the only third party;
its script loads only when the visitor reaches the booking section.

© Strata Cyber. All rights reserved.
