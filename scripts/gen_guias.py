#!/usr/bin/env python3
"""Genera /guias/ : indice externo de las guias sectoriales del blog de Plataforma IA.

Motivo (medido 2026-10-24): las guias sectoriales del blog (66 URLs en el sitemap) no
reciben ni un enlace externo, y el hub interno solo existe dentro de un post. Esta pagina
vive en el host del cluster de herramientas y da un enlace contextual (dofollow) a cada
guia que responde 200, agrupada por sector, con la pagina de servicio de ese sector.

Solo enlaza URLs verificadas por HTTP: nunca un 404.
Uso: python3 scripts/gen_guias.py   (desde la raiz del repo caseroclaw.github.io)
"""
from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

BLOG = Path("/home/hermes/plataforma-ia-blog")
POSTS = BLOG / "content" / "posts"
BASE = "https://plataformaia.com/es/blog/"
OUT = Path(__file__).resolve().parent.parent / "guias" / "index.html"

PILLARS = [
    ("/es/agentes-ia", "Agentes de IA para empresas", "qué atiende un agente, qué pasos ejecuta en tus sistemas y qué se queda en manos de una persona."),
    ("/es/automatizacion-ia", "Automatización de procesos con IA", "qué procesos conviene automatizar primero y cuáles no compensan."),
    ("/es/n8n", "Consultoría n8n", "cuándo la automatización se resuelve con flujos y cuándo hace falta un modelo en el bucle."),
    ("/es/consultoria-ia-madrid", "Consultoría de IA en Madrid", "cómo se trabaja un piloto de 4 semanas con métricas acordadas antes de empezar."),
    ("/es/casos-de-uso", "Casos de uso de IA", "atención, operaciones, conocimiento, contenido, datos y gobernanza."),
    ("/es/sectores", "IA por sector", "las 24 fichas sectoriales con procesos, límites legales y preguntas frecuentes."),
]


def sector_map() -> dict[str, tuple[str, str]]:
    src = (BLOG / "tools" / "internal_links.py").read_text(encoding="utf-8")
    rows = re.findall(r'^\s+"(automatizacion[^"]+)": \("/es/sectores/([^"]+)", "([^"]+)"\)', src, re.M)
    return {slug: (page, label) for slug, page, label in rows}


def title_of(slug: str) -> str:
    raw = (POSTS / f"{slug}.md").read_text(encoding="utf-8")
    m = re.search(r'^title: "(.*)"$', raw, re.M)
    return m.group(1) if m else slug


def alive(url: str) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PlataformaIA-index/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status == 200
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return False


def main() -> None:
    smap = sector_map()
    groups: dict[str, list[tuple[str, str]]] = {}
    dead = []
    for slug, (page, label) in sorted(smap.items()):
        url = BASE + slug
        if not alive(url):
            dead.append(slug)
            continue
        groups.setdefault(label, []).append((title_of(slug), url))
    total = sum(len(v) for v in groups.values())
    today = date.today().isoformat()

    rows = []
    for label in sorted(groups):
        guides = sorted(groups[label])
        links = " · ".join(
            f'<a href="{html.escape(u)}">{html.escape(t)}</a>' for t, u in guides
        )
        page = smap[[s for s, (p, l) in smap.items() if l == label][0]][0]
        page_url = "https://plataformaia.com/es/sectores/" + page
        cell = (
            f'<a href="{html.escape(page_url)}">ficha del sector</a>'
            if alive(page_url)
            else "ficha del sector (aún sin publicar)"
        )
        rows.append(
            f"      <tr><th scope=\"row\">{html.escape(label)}</th>"
            f"<td>{links}</td>"
            f"<td>{cell}</td></tr>"
        )

    pillar_items = "\n".join(
        f'      <li><a href="https://plataformaia.com{p}">{html.escape(t)}</a> — {html.escape(d)}</li>'
        for p, t, d in PILLARS
    )

    doc = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guías de automatización con IA por sector | Plataforma IA</title>
<meta name="description" content="Índice de {total} guías de automatización con IA por sector publicadas por Plataforma IA: qué procesos se automatizan, qué sigue siendo humano, coste y marco legal de cada uno.">
<link rel="canonical" href="https://caseroclaw.github.io/guias/">
<meta name="robots" content="index, follow">
<meta property="og:type" content="website">
<meta property="og:title" content="Guías de automatización con IA por sector">
<meta property="og:description" content="Índice de {total} guías sectoriales: procesos automatizables, límites legales y coste real.">
<meta property="og:url" content="https://caseroclaw.github.io/guias/">
<style>
  :root {{ --ink:#12161c; --muted:#5a6472; --line:#e3e7ec; --bg:#fff; --soft:#f7f9fc; --acc:#1a56db; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:900px; margin:0 auto; padding:0 20px; }}
  header {{ border-bottom:1px solid var(--line); padding:18px 0; }}
  header .wrap {{ display:flex; flex-wrap:wrap; gap:8px 18px; align-items:baseline; justify-content:space-between; }}
  .brand {{ font-weight:700; }}
  header a {{ color:var(--muted); text-decoration:none; font-size:14px; }}
  main {{ padding:38px 0 10px; }}
  h1 {{ font-size:1.9rem; line-height:1.25; margin:0 0 14px; }}
  h2 {{ font-size:1.25rem; margin:34px 0 12px; }}
  p {{ margin:0 0 14px; }}
  .lead {{ color:var(--muted); font-size:1.06rem; }}
  a {{ color:var(--acc); }}
  table {{ width:100%; border-collapse:collapse; margin:6px 0 18px; font-size:15px; }}
  th, td {{ text-align:left; padding:10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th[scope=row] {{ width:26%; color:var(--muted); font-weight:600; }}
  ul {{ margin:0 0 14px; padding-left:20px; }}
  li {{ margin:0 0 6px; }}
  footer {{ border-top:1px solid var(--line); margin-top:40px; padding:20px 0 40px; color:var(--muted); font-size:14px; }}
</style>
</head>
<body>
<header><div class="wrap">
  <span class="brand">Plataforma IA</span>
  <nav><a href="/">Herramientas gratuitas</a> · <a href="https://plataformaia.com/es/blog">Blog</a> · <a href="/privacidad/">Privacidad</a></nav>
</div></header>
<main class="wrap">
  <h1>Guías de automatización con IA, por sector</h1>
  <p class="lead">{total} guías publicadas por <a href="https://plataformaia.com">Plataforma IA</a>, consultora de automatización con IA para pymes en España. Cada una responde lo mismo: qué procesos se pueden automatizar hoy, qué sigue siendo humano, cuánto cuesta y qué norma hay que respetar en ese sector.</p>
  <p>Este índice existe porque el blog solo se puede navegar por fecha. Si vienes buscando tu sector, empieza por la fila que te toque y luego abre la ficha del sector para ver el alcance del servicio. Las guías se comprueban una a una antes de enlazarlas: aquí no hay enlaces a páginas que no existan.</p>

  <h2>Guías por sector</h2>
  <table>
    <caption class="lead" style="text-align:left;padding-bottom:8px">Sector · guía publicada · página de servicio</caption>
    <thead><tr><th scope="col">Sector</th><th scope="col">Guía</th><th scope="col">Servicio</th></tr></thead>
    <tbody>
{chr(10).join(rows)}
    </tbody>
  </table>

  <h2>Páginas de servicio</h2>
  <ul>
{pillar_items}
  </ul>

  <h2>Cómo leer estas guías</h2>
  <p>Ninguna promete un ahorro sin medirlo. Todas separan tres cosas que suelen mezclarse en las propuestas comerciales: lo que la IA hace sola, lo que hace con una persona revisando y lo que no debe tocarse. Y todas traen el coste con aritmética explícita —horas al mes, coste real de la hora y meses de amortización— para que puedas comprobar la cuenta con tus propios números.</p>
  <p>Si tu sector no está, <a href="https://plataformaia.com/es/contacto">escríbenos</a>: la guía se escribe cuando hay una pregunta real que responder, no para llenar el índice.</p>
</main>
<footer class="wrap">
  <p>Plataforma IA · <a href="https://plataformaia.com">plataformaia.com</a> · <a href="https://plataformaia.com/es/consultoria-ia-madrid">Consultoría de IA en Madrid</a> · <a href="https://plataformaia.com/es/contacto">Contacto</a></p>
  <p>Índice actualizado el {today}. Guías verificadas por HTTP antes de publicarse{'' if not dead else f'; {len(dead)} omitidas por no responder'}.</p>
</footer>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"guias: {total} en {len(groups)} sectores | omitidas: {len(dead)} {dead} | {len(doc)} bytes -> {OUT}")


if __name__ == "__main__":
    main()
