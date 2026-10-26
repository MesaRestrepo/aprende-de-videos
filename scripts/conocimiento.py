#!/usr/bin/env python3
"""Base de conocimiento local: notas en Markdown que tu IA puede guardar y consultar.

Carpeta (en orden): --kb, variable APRENDE_KB, o ~/.claude/conocimiento

    conocimiento.py guardar --titulo T --tema TEMA [--etiquetas a,b] [--fuente URL]
                            [--autor A] [--archivo notas.md]      (sin --archivo: lee stdin)
    conocimiento.py buscar CONSULTA [--max 5]
    conocimiento.py listar [--tema TEMA]
    conocimiento.py ver ID
    conocimiento.py borrar ID

ID = ruta relativa sin .md, por ejemplo  css/centrar-un-div
"""
import argparse
import os
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path


def kb_dir(arg):
    ruta = arg or os.environ.get("APRENDE_KB") or Path.home() / ".claude" / "conocimiento"
    ruta = Path(ruta).expanduser()
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def slug(t, largo=60):
    s = re.sub(r"[^a-z0-9]+", "-", sin_acentos(t).lower()).strip("-")
    return s[:largo].strip("-") or "sin-titulo"


def leer_nota(ruta):
    texto = ruta.read_text(encoding="utf-8")
    meta, cuerpo = {}, texto
    m = re.match(r"---\n(.*?)\n---\n?(.*)", texto, re.S)
    if m:
        for linea in m.group(1).splitlines():
            if ":" in linea:
                k, v = linea.split(":", 1)
                meta[k.strip()] = v.strip()
        cuerpo = m.group(2)
    return meta, cuerpo.strip()


def notas(kb):
    return sorted(p for p in kb.rglob("*.md") if p.name != "INDICE.md")


def id_de(kb, ruta):
    return ruta.relative_to(kb).with_suffix("").as_posix()


def reconstruir_indice(kb):
    por_tema = {}
    for p in notas(kb):
        meta, _ = leer_nota(p)
        por_tema.setdefault(meta.get("tema", "general"), []).append((p, meta))
    lineas = ["# Indice de conocimiento", "",
              f"{sum(len(v) for v in por_tema.values())} notas. "
              "Generado automaticamente, no editar a mano.", ""]
    for tema in sorted(por_tema):
        lineas += [f"## {tema}", ""]
        for p, meta in por_tema[tema]:
            et = f" `{meta['etiquetas']}`" if meta.get("etiquetas") else ""
            lineas.append(f"- **{id_de(kb, p)}** - {meta.get('titulo', p.stem)}{et}")
        lineas.append("")
    (kb / "INDICE.md").write_text("\n".join(lineas), encoding="utf-8")


def una_linea(t):
    return " ".join((t or "").split())


def cmd_guardar(a):
    kb = kb_dir(a.kb)
    cuerpo = Path(a.archivo).read_text(encoding="utf-8") if a.archivo else sys.stdin.read()
    if not cuerpo.strip():
        sys.exit("Nota vacia: pasa el contenido por stdin o con --archivo.")
    tema = slug(a.tema or "general")
    destino = kb / tema / f"{slug(a.titulo)}.md"
    accion = "creada"
    if a.fuente:  # misma fuente = misma nota, se actualiza en vez de duplicar
        for p in notas(kb):
            if leer_nota(p)[0].get("fuente") == a.fuente:
                destino, accion = p, "actualizada"
                break
    if accion == "creada" and destino.exists():
        accion = "actualizada"
    previo = leer_nota(destino)[0] if accion == "actualizada" else {}
    etiquetas = a.etiquetas or previo.get("etiquetas")
    autor = a.autor or previo.get("autor")
    fuente = a.fuente or previo.get("fuente")
    destino.parent.mkdir(parents=True, exist_ok=True)
    cab = ["---", f"titulo: {una_linea(a.titulo)}", f"tema: {tema}",
           f"etiquetas: {una_linea(etiquetas)}", f"fuente: {una_linea(fuente)}",
           f"autor: {una_linea(autor)}", f"fecha: {date.today().isoformat()}", "---", ""]
    destino.write_text("\n".join(cab) + cuerpo.strip() + "\n", encoding="utf-8")
    reconstruir_indice(kb)
    print(f"Nota {accion}: {id_de(kb, destino)}  ({destino})")


def puntuar(consulta, meta, cuerpo):
    palabras = [w for w in re.findall(r"\w+", sin_acentos(consulta.lower())) if len(w) > 2]
    if not palabras:
        return 0
    campos = [(sin_acentos(meta.get("titulo", "").lower()), 5),
              (sin_acentos(meta.get("etiquetas", "").lower()), 3),
              (sin_acentos(meta.get("tema", "").lower()), 2),
              (sin_acentos(cuerpo.lower()), 1)]
    return sum(texto.count(w) * peso for w in palabras for texto, peso in campos)


def fragmento(cuerpo, consulta, largo=220):
    plano = una_linea(cuerpo)
    base = sin_acentos(plano.lower())
    for w in re.findall(r"\w+", sin_acentos(consulta.lower())):
        i = base.find(w) if len(w) > 2 else -1
        if i >= 0:
            ini = max(0, i - 60)
            return ("..." if ini else "") + plano[ini:ini + largo] + "..."
    return plano[:largo] + ("..." if len(plano) > largo else "")


def cmd_buscar(a):
    kb = kb_dir(a.kb)
    res = []
    for p in notas(kb):
        meta, cuerpo = leer_nota(p)
        pts = puntuar(a.consulta, meta, cuerpo)
        if pts:
            res.append((pts, p, meta, cuerpo))
    res.sort(key=lambda r: -r[0])
    if not res:
        print("Sin resultados. Nada aprendido sobre eso todavia.")
        return
    for pts, p, meta, cuerpo in res[:a.max]:
        print(f"[{id_de(kb, p)}] {meta.get('titulo', p.stem)}  (puntos: {pts})")
        print(f"  fuente: {meta.get('fuente') or '-'}  autor: {meta.get('autor') or '-'}")
        print(f"  {fragmento(cuerpo, a.consulta)}\n")
    print("Leer una nota completa: conocimiento.py ver <id>")


def cmd_listar(a):
    kb = kb_dir(a.kb)
    n = 0
    for p in notas(kb):
        meta, _ = leer_nota(p)
        if a.tema and meta.get("tema") != slug(a.tema):
            continue
        n += 1
        print(f"{id_de(kb, p)}  |  {meta.get('titulo', p.stem)}  |  {meta.get('fecha', '')}")
    print(f"\n{n} notas en {kb}")


def resolver(kb, ident):
    ruta = (kb / f"{ident.removesuffix('.md')}.md").resolve()
    if kb.resolve() not in ruta.parents or not ruta.exists():
        sys.exit(f"No existe la nota '{ident}'. Usa 'listar' o 'buscar'.")
    return ruta


def cmd_ver(a):
    print(resolver(kb_dir(a.kb), a.id).read_text(encoding="utf-8"))


def cmd_borrar(a):
    kb = kb_dir(a.kb)
    resolver(kb, a.id).unlink()
    reconstruir_indice(kb)
    print(f"Borrada: {a.id}")


def main():
    for flujo in (sys.stdout, sys.stderr, sys.stdin):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--kb", help="carpeta de la base de conocimiento")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("guardar")
    g.add_argument("--titulo", required=True)
    g.add_argument("--tema", default="general")
    g.add_argument("--etiquetas")
    g.add_argument("--fuente")
    g.add_argument("--autor")
    g.add_argument("--archivo")
    g.set_defaults(f=cmd_guardar)

    b = sub.add_parser("buscar")
    b.add_argument("consulta")
    b.add_argument("--max", type=int, default=5)
    b.set_defaults(f=cmd_buscar)

    l = sub.add_parser("listar")
    l.add_argument("--tema")
    l.set_defaults(f=cmd_listar)

    v = sub.add_parser("ver")
    v.add_argument("id")
    v.set_defaults(f=cmd_ver)

    d = sub.add_parser("borrar")
    d.add_argument("id")
    d.set_defaults(f=cmd_borrar)

    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
