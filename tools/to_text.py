#!/usr/bin/env python3
"""把资料转换为纯文本并分块，供逐块精读。

用法:
    python3 tools/to_text.py inbox/某本书.epub knowledge/<slug>/_text [--chunk 12000]

支持: .txt .md .html/.htm .epub .docx .pdf
PDF 依次尝试 pdftotext 命令、pypdf 库；都没有时提示安装（或改用 Read 工具按页读取）。
输出: <out_dir>/full.txt 以及 chunk_001.txt ... ，并打印分块清单。
"""
import argparse
import html
import re
import shutil
import subprocess
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path


class _TextExtractor(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "section", "article", "blockquote",
             "h1", "h2", "h3", "h4", "h5", "h6", "pre"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
        if tag in ("h1", "h2", "h3"):
            self.parts.append("\n## " if tag == "h1" else "\n### ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(markup: str) -> str:
    p = _TextExtractor()
    p.feed(markup)
    return html.unescape("".join(p.parts))


def epub_to_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        container = z.read("META-INF/container.xml").decode("utf-8", "ignore")
        opf_path = re.search(r'full-path="([^"]+)"', container).group(1)
        opf = z.read(opf_path).decode("utf-8", "ignore")
        base = opf_path.rsplit("/", 1)[0] + "/" if "/" in opf_path else ""
        manifest = {}
        for item in re.finditer(r"<item\b[^>]*>", opf):
            tag = item.group(0)
            iid = re.search(r'\bid="([^"]+)"', tag)
            href = re.search(r'\bhref="([^"]+)"', tag)
            if iid and href:
                manifest[iid.group(1)] = href.group(1)
        order = re.findall(r'<itemref\b[^>]*idref="([^"]+)"', opf)
        texts = []
        for idref in order:
            href = manifest.get(idref)
            if not href:
                continue
            try:
                raw = z.read(base + href).decode("utf-8", "ignore")
            except KeyError:
                continue
            texts.append(html_to_text(raw))
        return "\n\n".join(texts)


def docx_to_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def pdf_to_text(path: Path) -> str:
    if shutil.which("pdftotext"):
        out = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                             capture_output=True, text=True, check=True)
        return out.stdout
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("无法解析 PDF：请安装 poppler-utils（pdftotext）或 `pip install pypdf`，"
                 "或直接用 Read 工具按页（每次≤20页）读取 PDF。")
    reader = PdfReader(str(path))
    return "\n".join(f"\n[第{i}页]\n{page.extract_text() or ''}"
                     for i, page in enumerate(reader.pages, 1))


def to_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".txt", ".md", ".markdown"):
        return path.read_text(encoding="utf-8", errors="ignore")
    if ext in (".html", ".htm", ".xhtml"):
        return html_to_text(path.read_text(encoding="utf-8", errors="ignore"))
    if ext == ".epub":
        return epub_to_text(path)
    if ext == ".docx":
        return docx_to_text(path)
    if ext == ".pdf":
        return pdf_to_text(path)
    sys.exit(f"不支持的格式: {ext}")


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("　", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def _pieces(text: str, size: int):
    """按段落拆分；超长段落再按行、按句、最后按长度硬切。"""
    for para in text.split("\n\n"):
        if len(para) <= size:
            yield para
            continue
        for line in re.split(r"(?<=\n)|(?<=[。！？.!?])", para):
            for i in range(0, len(line), size):
                yield line[i:i + size]


def chunk(text: str, size: int):
    """按段落切块，尽量不截断段落。"""
    chunks, buf, n = [], [], 0
    for para in _pieces(text, size):
        if n + len(para) > size and buf:
            chunks.append("\n\n".join(buf))
            buf, n = [], 0
        buf.append(para)
        n += len(para) + 2
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--chunk", type=int, default=12000, help="每块字符数（默认 12000）")
    args = ap.parse_args()

    text = normalize(to_text(args.source))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for old in args.out_dir.glob("chunk_*.txt"):
        old.unlink()
    (args.out_dir / "full.txt").write_text(text, encoding="utf-8")
    parts = chunk(text, args.chunk)
    for i, c in enumerate(parts, 1):
        (args.out_dir / f"chunk_{i:03d}.txt").write_text(c, encoding="utf-8")

    print(f"源文件: {args.source}  总字符: {len(text)}  分块: {len(parts)}")
    for i, c in enumerate(parts, 1):
        head = next((l.strip() for l in c.splitlines() if l.strip()), "")[:40]
        print(f"  chunk_{i:03d}  {len(c):>6} 字  {head}")


if __name__ == "__main__":
    main()
