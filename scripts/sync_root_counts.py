#!/usr/bin/env python3
"""Sincroniza los recuentos del pie del índice raíz con lo que sirven /guias/ y /recursos/.

Por qué existe: los generadores de /guias/ (gen_guias.py) y /recursos/ (gen_recursos.py)
recalculan sus cifras leyendo el estado real del blog, pero el pie de `index.html` las
llevaba escritas a mano. Cuando el blog cambió (poda de guías el 27-oct: 45 -> 40), el
índice raíz siguió afirmando 45 y 17 durante cinco días mientras /guias/ y /recursos/
decían 40 y 19. Este script cierra esa deriva: cuenta los enlaces de blog realmente
servidos por los dos índices generados y reescribe los números del pie de la raíz.

Uso:  python3 scripts/sync_root_counts.py        (idempotente; escribe solo si cambia)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
PAGES = {"guias": ROOT / "guias" / "index.html", "recursos": ROOT / "recursos" / "index.html"}

BLOG = re.compile(r"https://plataformaia\.com/es/blog/[a-z0-9\-]+")
# Texto exacto del pie que hay que mantener honesto.
PATTERNS = {
    "guias": re.compile(r"(\d+)( guías de automatización con IA por sector)"),
    "recursos": re.compile(r"(\d+)( guías por problema)"),
}


def count(page: Path) -> int:
    html = page.read_text(encoding="utf-8")
    return len(set(BLOG.findall(html)))


def main() -> int:
    missing = [str(p) for p in [INDEX, *PAGES.values()] if not p.exists()]
    if missing:
        print("faltan ficheros: " + ", ".join(missing), file=sys.stderr)
        return 1

    counts = {name: count(page) for name, page in PAGES.items()}
    html = INDEX.read_text(encoding="utf-8")
    original = html

    for name, pattern in PATTERNS.items():
        n = counts[name]
        matches = pattern.findall(html)
        if len(matches) != 1:
            print(
                f"AVISO: '{name}' aparece {len(matches)} veces en index.html (se esperaba 1); no se toca",
                file=sys.stderr,
            )
            continue
        old = int(matches[0][0])
        html = pattern.sub(lambda m: f"{n}{m.group(2)}", html, count=1)
        state = "sin cambios" if old == n else f"{old} -> {n}"
        print(f"{name}: {state}")

    if html != original:
        INDEX.write_text(html, encoding="utf-8")
        print(f"index.html reescrito ({len(html)} bytes)")
    else:
        print("index.html sin cambios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
