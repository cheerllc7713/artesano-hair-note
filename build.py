#!/usr/bin/env python3
"""ARTESANO HAIR NOTE の静的サイトビルダー。
content/posts/*.md と content/pages/*.md を dist/ に HTML として書き出す。
使い方: python3 build.py
"""
import datetime as dt
import pathlib
import re
import shutil

import jinja2
import markdown
import yaml

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "dist"

CATEGORIES = {
    "kaizen": "髪質改善",
    "color": "カラー",
    "homecare": "ホームケア",
    "item": "アイテム",
    "local": "流山・江戸川台",
}


def read_md(path, render=None):
    text = path.read_text(encoding="utf-8")
    if render:
        text = render(text)
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    meta, body = (yaml.safe_load(m.group(1)), m.group(2)) if m else ({}, text)
    md = markdown.Markdown(extensions=["tables", "toc", "attr_list", "md_in_html"],
                           extension_configs={"toc": {"toc_depth": "2-2"}})
    meta["html"] = md.convert(body)
    meta["toc"] = md.toc_tokens
    meta["slug"] = path.stem
    meta["chars"] = len(re.sub(r"\s", "", body))
    return meta


def main():
    site = yaml.safe_load((ROOT / "site.yml").read_text(encoding="utf-8"))
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(ROOT / "templates"),
                             autoescape=jinja2.select_autoescape(["html"]))
    env.filters["cat"] = lambda c: CATEGORIES.get(c, c)
    env.filters["jdate"] = lambda d: f"{d.year}年{d.month}月{d.day}日"

    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "posts").mkdir(parents=True)
    shutil.copytree(ROOT / "static", DIST / "static")

    posts = [read_md(p) for p in sorted((ROOT / "content/posts").glob("*.md"))]
    posts = [p for p in posts if not p.get("draft")]
    posts.sort(key=lambda p: p["date"], reverse=True)
    for p in posts:
        p["minutes"] = max(1, round(p["chars"] / 500))

    common = dict(site=site, categories=CATEGORIES, year=dt.date.today().year)

    for p in posts:
        related = [q for q in posts if q is not p and q["category"] == p["category"]][:3]
        if len(related) < 3:
            related += [q for q in posts if q is not p and q not in related][: 3 - len(related)]
        html = env.get_template("post.html").render(post=p, related=related, root="../", **common)
        (DIST / "posts" / f"{p['slug']}.html").write_text(html, encoding="utf-8")

    for path in sorted((ROOT / "content/pages").glob("*.md")):
        pg = read_md(path, render=lambda t: env.from_string(t).render(site=site))
        html = env.get_template("page.html").render(page=pg, root="", **common)
        (DIST / f"{pg['slug']}.html").write_text(html, encoding="utf-8")

    html = env.get_template("index.html").render(posts=posts, root="", **common)
    (DIST / "index.html").write_text(html, encoding="utf-8")

    # sitemap
    urls = [f"{site['url']}/"] + [f"{site['url']}/posts/{p['slug']}.html" for p in posts]
    sm = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    (DIST / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>',
        encoding="utf-8")
    print(f"built {len(posts)} posts -> {DIST}")


if __name__ == "__main__":
    main()
