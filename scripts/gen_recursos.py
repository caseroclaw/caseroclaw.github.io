#!/usr/bin/env python3
"""Genera /recursos/ : indice externo de las guias del blog que NO son sectoriales.

Motivo (medido 2026-10-25): de las 66 URLs de blog del sitemap, 45 estan en /guias/
y 18 no reciben ni un enlace externo desde ningun sitio (ni del cluster de Pages ni de
otro dominio). Entre esas 18 estan tres de las paginas con mas intencion comercial del
blog (agentes de voz, elegir consultora, precios y margenes) y toda la normativa
(VeriFactu B2B, RD 723/2026, calidad del dato, formacion).

Esta pagina cierra ese hueco con el mismo criterio que /guias/: solo enlaza lo que
responde 200, agrupado por el momento en el que se busca (empezar, atender, cobrar,
cumplir, vender). Los textos salen del frontmatter del propio post (title y
meta_description), no se inventan.

Uso: python3 scripts/gen_recursos.py   (desde la raiz del repo caseroclaw.github.io)
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
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "recursos" / "index.html"
SITEMAP = "https://plataformaia.com/sitemap.xml"
GUIAS = "https://caseroclaw.github.io/guias/"
RAIZ = "https://caseroclaw.github.io/"

# Grupo editorial por slug. Lo que no esta aqui cae en «Otras guias» y aun asi se
# publica: el indice no depende de que yo recuerde clasificarlo.
GROUPS = {
    "indices": [
        "automatizacion-ia-pymes-espana-guia-completa-sector",
        "ia-open-source-pymes-espana-herramientas",
    ],
    "empezar": [
        "elegir-consultora-automatizacion-ia-espana",
        "geo-pymes",
        "calidad-datos-ia-pymes",
        "formacion-adopcion-ia-pymes",
        "ia-precios-margenes-pymes",
        "ayudas-ia-automatizacion-pymes-kit-digital-consulting",
    ],
    "atender": [
        "agentes-voz-ia-pymes",
        "asistentes-ia-atencion-cliente-pymes",
        "automatizacion-procesos-backoffice-ia-pymes",
    ],
    "cobrar": [
        "ia-gestion-cobros-morosity-pymes",
        "factura-electronica-b2b-obligatoria-pymes-espana",
    ],
    "cumplir": [
        "rd-723-2026-algoritmos-empresas",
    ],
    "vender": [
        "ia-prospectacion-comercial-leads-pymes",
    ],
    "sectores-sueltos": [
        "automatizacion-ia-ayuda-domicilio-sad-espana",
        "automatizacion-ia-funerarias-tanatorios-espana",
        "automatizacion-ia-lavanderias-tintorerias-espana",
        "automatizacion-ia-transporte-mercancias-deca-digital-espana",
    ],
}

LABELS = {
    "indices": ("Índices y comparativas del blog", "la guía completa por sector y la comparativa de herramientas open-source: las dos páginas de referencia que se citan enteras."),
    "empezar": ("Empezar con IA sin equivocarte", "elegir proveedor, saber si el dato esta listo, formar al equipo y calcular si el proyecto se paga."),
    "atender": ("Atender mejor sin ampliar plantilla", "que hace un agente de voz o de WhatsApp, cuanto del volumen absorbe y donde tiene que entrar una persona."),
    "cobrar": ("Cobrar antes y facturar sin sustos", "recordatorios de impago, factura electronica B2B obligatoria y el calendario de VeriFactu."),
    "cumplir": ("Cumplir la normativa que ya esta en vigor", "obligaciones que empiezan a contar en una fecha concreta y que afectan a quien automatiza."),
    "vender": ("Vender con menos trabajo manual", "prospeccion, seguimiento y leads que se pierden por no contestar."),
    "sectores-sueltos": ("Sectores con guia propia fuera del indice sectorial", "transporte, ayuda a domicilio, funerarias y lavanderias: mismos procesos, distinto marco legal."),
    "otros": ("Otras guías del blog", "articulos publicados que no encajan en los bloques anteriores."),
}

# Paginas del sitemap que no son guias y por tanto no entran en un indice de guias.
# `politica-editorial` se enlaza desde /privacidad/ (pagina de confianza), no desde aqui.
EXCLUDE = {"politica-editorial"}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PlataformaIA-index/1.0)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def fetch_state(url: str) -> str:
    """ok / noindex / dead. Un 200 con `noindex` no es enlazable en un indice."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PlataformaIA-index/1.0)"})
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


def frontmatter_value(raw: str, field: str) -> str:
    m = re.search(rf'^{field}: "(.*)"$', raw, re.M)
    return m.group(1) if m else ""


def main() -> None:
    sm = get(SITEMAP)
    blog = sorted(set(re.findall(r"<loc>(https://plataformaia\.com/es/blog/[^<]+)</loc>", sm)))
    try:
        guias_html = get(GUIAS)
    except urllib.error.URLError:
        guias_html = ""
    try:
        raiz_html = get(RAIZ)
    except urllib.error.URLError:
        raiz_html = ""

    orphans = []
    for url in blog:
        if url in guias_html or url in raiz_html:
            continue
        slug = url.rsplit("/", 1)[-1]
        if slug in EXCLUDE:
            continue
        orphans.append(slug)

    by_group: dict[str, list[tuple[str, str, str]]] = {}
    skipped, missing = [], []
    for slug in orphans:
        path = POSTS / f"{slug}.md"
        if not path.exists():
            missing.append(slug)
            continue
        if fetch_state(BASE + slug) != "ok":
            skipped.append(slug)
            continue
        raw = path.read_text(encoding="utf-8")
        title = frontmatter_value(raw, "title") or slug
        desc = frontmatter_value(raw, "meta_description")
        group = next((g for g, slugs in GROUPS.items() if slug in slugs), "otros")
        by_group.setdefault(group, []).append((title, BASE + slug, desc))

    order = ["indices", "empezar", "atender", "cobrar", "cumplir", "vender", "sectores-sueltos", "otros"]
    total = sum(len(v) for v in by_group.values())
    today = date.today().isoformat()

    sections = []
    for g in order:
        items = by_group.get(g)
        if not items:
            continue
        label, lead = LABELS[g]
        lis = "\n".join(
            f'      <li><a href="{html.escape(u)}">{html.escape(t)}</a>'
            + (f" — {html.escape(d)}" if d else "")
            + "</li>"
            for t, u, d in sorted(items)
        )
        sections.append(
            f'  <h2>{html.escape(label)}</h2>\n'
            f'  <p class="lead">{html.escape(lead)}</p>\n'
            f"  <ul>\n{lis}\n  </ul>"
        )

    doc = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guías de IA para pymes: atención, cobros, normativa y datos | Plataforma IA</title>
<meta name="description" content="Índice de {total} guías de Plataforma IA sobre IA en la pyme: cómo elegir proveedor, qué atiende un agente, cómo cobrar antes, qué exige la normativa y qué datos necesitas antes de automatizar.">
<link rel="canonical" href="https://caseroclaw.github.io/recursos/">
<meta name="robots" content="index, follow">
<meta property="og:type" content="website">
<meta property="og:title" content="Guías de IA para pymes: atención, cobros, normativa y datos">
<meta property="og:description" content="Índice de {total} guías: proveedor, agentes, cobros, normativa y calidad del dato.">
<meta property="og:url" content="https://caseroclaw.github.io/recursos/">
<style>
  :root {{ --ink:#12161c; --muted:#5a6472; --line:#e3e7ec; --bg:#fff; --acc:#1a56db; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:860px; margin:0 auto; padding:0 20px; }}
  header {{ border-bottom:1px solid var(--line); padding:18px 0; }}
  header .wrap {{ display:flex; flex-wrap:wrap; gap:8px 18px; align-items:baseline; justify-content:space-between; }}
  .brand {{ font-weight:700; }}
  header a {{ color:var(--muted); text-decoration:none; font-size:14px; }}
  main {{ padding:38px 0 10px; }}
  h1 {{ font-size:1.9rem; line-height:1.25; margin:0 0 14px; }}
  h2 {{ font-size:1.2rem; margin:32px 0 6px; }}
  p {{ margin:0 0 14px; }}
  .lead {{ color:var(--muted); font-size:.98rem; margin-bottom:10px; }}
  a {{ color:var(--acc); }}
  ul {{ margin:0 0 16px; padding-left:20px; }}
  li {{ margin:0 0 8px; }}
  footer {{ border-top:1px solid var(--line); margin-top:40px; padding:20px 0 40px; color:var(--muted); font-size:14px; }}
</style>
</head>
<body>
<header><div class="wrap">
  <span class="brand">Plataforma IA</span>
  <nav><a href="/">Herramientas gratuitas</a> · <a href="/guias/">Guías por sector</a> · <a href="https://plataformaia.com/es/blog">Blog</a> · <a href="/privacidad/">Privacidad</a></nav>
</div></header>
<main class="wrap">
  <h1>Guías de IA para pymes, por el problema que resuelven</h1>
  <p class="lead">Estas {total} guías las publica <a href="https://plataformaia.com">Plataforma IA</a>, consultora de automatización con IA para pymes en España. Aquí están las que no son de un sector concreto: cómo elegir proveedor, qué hace un agente, cómo se cobra antes, qué exige la norma y qué hay que arreglar en los datos antes de automatizar.</p>
  <p>Si buscas tu sector, el índice está en <a href="/guias/">las guías por sector</a>. Este índice se regenera comprobando por HTTP cada enlace: lo que no responde 200 no se publica.</p>

{chr(10).join(sections)}

  <h2>Antes de contratar nada</h2>
  <p>Dos herramientas gratuitas que evitan la conversación de venta: la <a href="/roi-automatizacion-ia/">calculadora de ROI</a> pone cifra a un proceso manual con el coste real de la hora y dice en cuántos meses se amortiza; el <a href="/radar-ai-act/">clasificador del AI Act</a> dice si el sistema que quieres implantar es de alto riesgo y qué deberes tienes por tu rol.</p>
</main>
<footer class="wrap">
  <p>Plataforma IA · <a href="https://plataformaia.com">plataformaia.com</a> · <a href="https://plataformaia.com/es/consultoria-ia-madrid">Consultoría de IA en Madrid</a> · <a href="https://plataformaia.com/es/contacto">Contacto</a></p>
  <p>Índice actualizado el {today}. {total} guías verificadas por HTTP{'' if not skipped else f'; {len(skipped)} omitidas por no responder'}.</p>
</footer>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"recursos: {total} guias en {len(by_group)} bloques | huerfanas detectadas: {len(orphans)} | omitidas 404: {skipped} | sin fichero: {missing} | {len(doc)} bytes")


if __name__ == "__main__":
    main()
