#!/usr/bin/env python3
"""Genera el sitemap.xml del cluster de Pages con la lista REAL de paginas vivas.

Motivo (medido 2026-10-31): el sitemap declaraba 4 URLs y dejaba fuera las tres
herramientas que son el nucleo del cluster (`/roi-automatizacion-ia/`,
`/radar-ai-act/`, `/verifactu-qr-web/`, las tres 200 y enlazadas desde la raiz), y
seguia diciendo `lastmod 2026-10-23..25` aunque `/guias/` se regenera cada semana: un
lastmod mas viejo que el cambio real le dice al rastreador que no vuelva.

Reglas:
- Solo entra una URL si responde 200 hoy y no lleva `noindex` (mismo criterio que los
  indices `/guias/` y `/recursos/`).
- `lastmod` sale del ultimo commit que toco el fichero en su repo, no de una constante.
  Si el fichero no esta en git, se usa su mtime; si tampoco, la fecha de hoy.

Uso: python3 scripts/gen_sitemap.py   (desde la raiz del repo caseroclaw.github.io)
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

HOST = "https://caseroclaw.github.io"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sitemap.xml"

# (ruta, fichero local, prioridad, changefreq)
PAGES = [
    ("/", ROOT / "index.html", "1.0", "weekly"),
    ("/guias/", ROOT / "guias" / "index.html", "0.9", "weekly"),
    ("/recursos/", ROOT / "recursos" / "index.html", "0.9", "weekly"),
    ("/roi-automatizacion-ia/", Path("/home/hermes/roi-automatizacion-ia/index.html"), "0.9", "monthly"),
    ("/radar-ai-act/", Path("/home/hermes/radar-ai-act/index.html"), "0.9", "monthly"),
    ("/verifactu-qr-web/", Path("/home/hermes/verifactu-qr-web/index.html"), "0.8", "monthly"),
    ("/privacidad/", ROOT / "privacidad" / "index.html", "0.5", "yearly"),
]


def state(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PlataformaIA-sitemap/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            if r.status != 200:
                return "dead"
            body = r.read().decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return "dead"
    m = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)', body, re.I)
    if m and "noindex" in m.group(1).lower():
        return "noindex"
    return "ok"


def lastmod(path: Path) -> str:
    if path.exists():
        try:
            dirty = subprocess.run(
                ["git", "-C", str(path.parent), "status", "--porcelain", "--", path.name],
                capture_output=True, text=True, timeout=20,
            )
            if dirty.returncode == 0 and dirty.stdout.strip():
                return dt.date.today().isoformat()  # cambio sin commitear = cambio de hoy
            out = subprocess.run(
                ["git", "-C", str(path.parent), "log", "-1", "--format=%cs", "--", path.name],
                capture_output=True, text=True, timeout=20,
            )
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except Exception:
            pass
        return dt.date.fromtimestamp(path.stat().st_mtime).isoformat()
    return dt.date.today().isoformat()


def main() -> None:
    entries, skipped, report = [], [], []
    for route, path, prio, freq in PAGES:
        url = HOST + route
        if state(url) != "ok":
            skipped.append(route)
            continue
        lm = lastmod(path)
        report.append((url, lm))
        entries.append(
            "  <url>\n"
            f"    <loc>{url}</loc>\n"
            f"    <lastmod>{lm}</lastmod>\n"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{prio}</priority>\n"
            "  </url>"
        )
    doc = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
    OUT.write_text(doc, encoding="utf-8")
    print(f"sitemap: {len(entries)} URLs | omitidas: {skipped} | {len(doc)} bytes")
    for url, lm in report:
        print(" ", url, lm)


if __name__ == "__main__":
    main()
