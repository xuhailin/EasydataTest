#!/usr/bin/env python3
"""Build an explicitly selected, portable static showcase; never run course code."""
import json
import posixpath
import re
import shutil
import tempfile
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import markdown
from markdown.treeprocessors import Treeprocessor

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
OUTPUT = ROOT / "_site"


def relative(target, page):
    return quote(posixpath.relpath(target, posixpath.dirname(page) or "."), safe="/")


def selected_file(folder, name):
    path = folder / name
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(folder.resolve()) or path.is_symlink():
        raise ValueError(f"Publication path must stay inside {folder}: {name}")
    if not resolved.is_file():
        raise ValueError(f"Not a file: {name}")
    return resolved


class PublicationLinks(Treeprocessor):
    def __init__(self, md, source, page, mapping):
        super().__init__(md)
        self.source, self.page, self.mapping = source, page, mapping

    def run(self, root):
        for element in root.iter():
            for attribute in ("href", "src"):
                value = element.get(attribute)
                if value is None:
                    continue
                url = urlsplit(value)
                if url.scheme in ("https", "http", "mailto"):
                    continue
                if url.scheme or url.netloc or url.path.startswith("/"):
                    raise ValueError(f"Unsupported public URL in {self.source}: {value}")
                if not url.path:
                    continue
                source_target = (self.source.parent / unquote(url.path)).resolve()
                if source_target not in self.mapping:
                    raise ValueError(f"Link target is not selected for publication: {value} ({self.source})")
                href = relative(self.mapping[source_target], self.page)
                if url.query:
                    href += "?" + url.query
                if url.fragment:
                    href += "#" + url.fragment
                element.set(attribute, href)


def render(source, page, mapping):
    text = source.read_text(encoding="utf-8")
    text = re.sub(r"\A# [^\n]*\n", "", text, count=1)
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
    md.treeprocessors.register(PublicationLinks(md, source, page, mapping), "public_links", 1)
    html = md.convert(text)
    return html.replace("<table>", '<div class="table-scroll" tabindex="0" role="region" aria-label="数据表格"><table>').replace("</table>", "</table></div>")


def state(task):
    if task.get("result") and task.get("notes"):
        return "成果与心得已收录"
    if task.get("result"):
        return "成果已收录"
    if task.get("notes"):
        return "心得已收录"
    return "待补充" if task["id"] != 10 else "预留"


def layout(title, description, body, page):
    home, css = relative("index.html", page), relative("style.css", page)
    icon = relative("favicon.svg", page)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{escape(description, quote=True)}">
<title>{escape(title)} · EasyData 学习手记</title>
<link rel="icon" href="{icon}" type="image/svg+xml">
<link rel="stylesheet" href="{css}"></head><body>
<a class="skip" href="#main">跳到正文</a>
<header><div class="bar"><a class="brand" href="{home}">EasyData <small>学习手记</small></a>
<nav aria-label="主导航"><a href="{home}#tasks">任务目录</a><a href="https://datawhalechina.github.io/easy-data-x-ai/">官方课程 ↗</a></nav></div></header>
<main id="main" class="wrap">{body}</main>
<footer class="site-footer"><span>Hailin · Easy Data × AI</span><span>记录成果，也记录理解的过程。</span></footer>
</body></html>'''


class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if key in attrs:
                self.links.append(attrs[key])


def validate(output):
    pages = {}
    for path in output.rglob("*.html"):
        parser = PageLinks()
        parser.feed(path.read_text(encoding="utf-8"))
        pages[path.resolve()] = parser
    for path, parser in pages.items():
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme in ("https", "http", "mailto"):
                continue
            if url.scheme or url.netloc or url.path.startswith("/"):
                raise ValueError(f"Non-portable link in {path}: {link}")
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if target.is_dir():
                target /= "index.html"
            if not target.is_relative_to(output.resolve()) or not target.is_file():
                raise ValueError(f"Broken public link in {path}: {link}")
            if url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                raise ValueError(f"Missing anchor in {path}: {link}")
    return len(pages)


def build():
    tasks = json.loads((SITE / "tasks.json").read_text(encoding="utf-8"))
    ids = [task["id"] for task in tasks]
    if ids != list(range(1, len(ids) + 1)):
        raise ValueError("Task IDs must be unique and sequential, starting at 1")
    mapping, sources, attachments = {}, {}, {}
    for task in tasks:
        number = task["id"]
        folder = ROOT / "tasks" / f"task{number}"
        page = f"task{number}/index.html"
        for field in ("result", "notes"):
            if task.get(field):
                source = selected_file(folder, task[field])
                if source.suffix != ".md" or source.name in ("submission.md", "README.md"):
                    raise ValueError("Only dedicated showcase and notes Markdown may be published")
                sources[number, field] = source
                mapping[source] = page
        for name in task.get("attachments", []):
            source = selected_file(folder, name)
            if source.suffix.lower() not in (".txt", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf"):
                raise ValueError(f"Unsupported attachment: {name}")
            target = f"task{number}/{name}"
            mapping[source] = target
            attachments[source] = target

    with tempfile.TemporaryDirectory(prefix="easydata-site-") as temporary:
        output = Path(temporary)
        shutil.copyfile(SITE / "style.css", output / "style.css")
        shutil.copyfile(SITE / "favicon.svg", output / "favicon.svg")
        (output / ".nojekyll").touch()
        for source, target in attachments.items():
            destination = output / target
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        rows = []
        for task in tasks:
            number, title = task["id"], escape(task["title"])
            page = f"task{number}/index.html"
            available = " available" if task.get("result") or task.get("notes") else ""
            rows.append(f'''<a class="task-row" href="task{number}/">
<span class="task-no">{number:02d}</span><div><h3>{title}</h3><span class="chapters">{escape(task['chapters'])}</span></div>
<span class="state{available}">{state(task)}</span><span class="arrow" aria-hidden="true">↗</span></a>''')
            sections = []
            for field, section_id, heading in (("result", "results", "实践成果"), ("notes", "notes", "学习心得")):
                if (number, field) in sources:
                    content = f'<div class="prose">{render(sources[number, field], page, mapping)}</div>'
                else:
                    message = "本任务尚未收录实践成果。" if field == "result" else "心得将在学习后补充。"
                    content = f'<p class="empty">{message}</p>'
                sections.append(f'<section id="{section_id}"><h2 class="section-title">{heading}</h2>{content}</section>')
            previous = f'<a href="../task{number-1}/">← Task {number-1:02d}</a>' if number > 1 else '<a href="../index.html#tasks">← 任务目录</a>'
            following = f'<a href="../task{number+1}/">Task {number+1:02d} →</a>' if number < len(tasks) else '<a href="../index.html#tasks">返回目录 →</a>'
            body = f'''<div class="task-intro"><a class="back" href="../index.html#tasks">← 全部任务</a>
<p class="eyebrow">学习手记 / TASK {number:02d}</p><h1>{title}</h1>
<div class="task-meta"><span class="chapters">{escape(task['chapters'])}</span><span class="state{available}">{state(task)}</span></div></div>
<div class="reading"><nav class="section-nav" aria-label="页内导航"><small>本篇内容</small><a href="#results">01　实践成果</a><a href="#notes">02　学习心得</a><a href="../index.html#tasks">全部任务 ↗</a></nav>
<div class="content">{''.join(sections)}<nav class="pager" aria-label="相邻任务">{previous}{following}</nav></div></div>'''
            destination = output / page
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(layout(f"Task {number}：{task['title']}", f"Task {number} 的实践成果与学习心得。{state(task)}。", body, page), encoding="utf-8")
        count = sum(bool(task.get("result") or task.get("notes")) for task in tasks)
        body = f'''<section class="intro"><p class="eyebrow">HAILIN / EASY DATA × AI</p><h1>学习成果与心得</h1><p>从环境准备到 Agent 实践，按 Task 留下运行结果、学习笔记与阶段性理解。</p></section>
<section id="tasks" aria-labelledby="tasks-title"><div class="index-head"><h2 id="tasks-title">任务目录</h2><span>{len(tasks)} 个任务入口 · {count} 篇已有内容</span></div>{''.join(rows)}</section>'''
        (output / "index.html").write_text(layout("任务目录", "Hailin 的 Easy Data × AI 学习成果与心得，按 Task 归档。", body, "index.html"), encoding="utf-8")
        total = validate(output)
        if OUTPUT.is_symlink():
            raise ValueError("Refusing to replace a symlink at _site")
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        shutil.copytree(output, OUTPUT)
        print(f"Built {total} pages and {len(attachments)} selected attachment(s) in {OUTPUT}")
        print("All local links and anchors validated. No task code or model API was executed.")


if __name__ == "__main__":
    build()
