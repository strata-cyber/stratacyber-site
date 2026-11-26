# Publishing an article

There is no admin panel. An article is a Markdown file in `content/articles/en/` (English)
or `content/articles/pt/` (Portuguese). Commit it to `main` and the site rebuilds and deploys
itself within a couple of minutes.

1. Copy `content/articles/_template.md` into `en/` or `pt/` and rename it. The file name becomes the URL:
   - `en/ransomware-healthcare.md` → `stratacyber.com.br/articles/ransomware-healthcare/`
   - `pt/ransomware-healthcare.md` → `stratacyber.com.br/pt/articles/ransomware-healthcare/`

   Use lowercase letters, digits and hyphens only, and an **English** name in both folders.
   The same file name in `en/` and `pt/` makes the two versions link to each other.
2. Fill in the block between the `+++` lines (it is [TOML](https://toml.io)):

   | Key | Required | Notes |
   |---|---|---|
   | `title` | yes | |
   | `summary` | yes | One or two sentences. Used in lists, search results and link previews. |
   | `date` | yes | `2026-12-01`, no quotes. A future date publishes automatically on that day. |
   | `kind` | | Label above the title: `"Analysis"`, `"Advisory"`, `"Method"`… |
   | `author` | | |
   | `tlp` | | Only `"CLEAR"`. The build refuses any other label (see below). |
   | `severity` | | `"critical"`, `"high"`, `"medium"`, `"low"`, `"info"` |
   | `draft` | | `true` keeps it off the site. |
   | `updated` | | Date of a meaningful revision. |

3. Write the body in Markdown below the second `+++`.
4. Commit and push. That's it.

To unpublish: set `draft = true`, or delete the file.

The site is public, so it is `TLP:CLEAR` by definition. The build fails if an article is labelled
`RED`, `AMBER+STRICT`, `AMBER` or `GREEN`: that content must not be published, only sanitised versions of it.

## What Markdown renders as

| You write | You get |
|---|---|
| `## Heading` | Section heading in Garnet (also listed in the article's side contents when there are 3+) |
| `> quote` | Quote with the garnet spine. Use it for key judgments. |
| `` `TLP:AMBER` `` | A real TLP label, FIRST colours |
| `<span class="sev sev-high">High</span>` | A severity label (`critical`, `high`, `medium`, `low`, `info`) |
| `!!! note "Title"` + indented text | Garnet Tint callout box |
| Fenced ```` ``` ```` block | Ink code block. Defang indicators: `example[.]com`, `hxxps://` |
| Tables, footnotes `[^1]`, `*italic*`, `**bold**` | As expected |

For example indicators, use names and addresses that cannot belong to anyone:
domains ending in `.example`, and IPs from `192.0.2.0/24`, `198.51.100.0/24` or `203.0.113.0/24`.

## Images

Make a folder with the same name as the article file and put images in it:

```
content/articles/en/ransomware-healthcare.md
content/articles/en/ransomware-healthcare/chart.png
```

Then reference it by name: `![Description of the chart](chart.png)`. Always write the description:
the build fails on an image without one. The folder takes images (`.png`, `.jpg`, `.webp`, `.avif`, `.gif`,
`.svg` without scripts) and `.pdf` files only.

## Preview before publishing (optional)

```
python build.py serve --drafts
```

Open http://localhost:8000. `--drafts` also shows drafts and future-dated articles.

## Voice (from the brand guidelines)

- **Specific**: "Three ransomware groups hit the sector this month", not "the threat landscape has never been so dangerous".
- **Prioritises**: "Block these four domains today", not "heightened vigilance is advised".
- **Calibrated**: "Likely (55–80%), with moderate confidence", never "this will definitely happen".
- **Composed**: "The risk is high and three actions reduce it", not "hackers could strike at any moment".
