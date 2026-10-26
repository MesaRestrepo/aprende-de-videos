#!/usr/bin/env python3
"""Convierte un video (URL o archivo) en material que una IA puede leer.

Entradas aceptadas:
    - URL de Reel, TikTok, YouTube/Short, X, Facebook... (cualquier sitio de yt-dlp)
    - archivo local de video, audio o imagen (capturas, grabaciones de pantalla)

Salida, dentro de la carpeta elegida:
    material.md        todo junto: datos, transcripcion con tiempos, lista de frames
    transcripcion.txt  lo que se dice, con marcas [m:ss]
    info.json          metadatos
    frames/            capturas con su segundo en el nombre (f_001_t00s.jpg)

Uso:
    procesar_video.py URL_O_ARCHIVO [...] [--salida CARPETA]
    procesar_video.py --verificar
"""
import argparse
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import warnings
from pathlib import Path
from urllib.parse import urlparse

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
warnings.filterwarnings("ignore")

VIDEO = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".flv"}
AUDIO = {".mp3", ".m4a", ".wav", ".ogg", ".opus", ".aac", ".flac"}
IMAGEN = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


class Fallo(Exception):
    """Error esperado: se muestra el mensaje, sin traza."""


def ejecutar(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise Fallo((r.stderr or r.stdout).strip()[-1500:])
    return r.stdout


def pista_de_error(texto):
    t = texto.lower()
    if "sign in" in t or "not a bot" in t or "log in" in t or "login" in t \
            or "cookies" in t or "empty media response" in t:
        return ("La plataforma pide sesion o bloquea la descarga automatica.\n"
                "Opciones:\n"
                "  1. Reintenta con tus cookies:  --cookies-navegador chrome  (o firefox, edge)\n"
                "     o  --cookies-archivo cookies.txt\n"
                "  2. Descarga o graba el video tu mismo y pasa el ARCHIVO en vez de la URL.")
    if "private" in t or "unavailable" in t or "not available" in t:
        return "El video es privado, fue borrado o no esta disponible en tu pais."
    if "unsupported url" in t:
        return "Enlace no soportado. Debe ser un video, no un perfil ni una busqueda."
    if "429" in t or "too many requests" in t:
        return "La plataforma limito tus peticiones. Espera unos minutos o usa cookies."
    return "Actualiza yt-dlp (las plataformas cambian a diario):  python -m pip install -U yt-dlp"


def duracion(ruta):
    if not shutil.which("ffprobe"):
        return None
    try:
        return float(ejecutar(["ffprobe", "-v", "error", "-show_entries",
                               "format=duration", "-of", "csv=p=0", str(ruta)]).strip())
    except (Fallo, ValueError):
        return None


def tiene_audio(ruta):
    if not shutil.which("ffprobe"):
        return True
    try:
        return bool(ejecutar(["ffprobe", "-v", "error", "-select_streams", "a",
                              "-show_entries", "stream=index", "-of", "csv=p=0",
                              str(ruta)]).strip())
    except Fallo:
        return True


def mmss(seg):
    seg = int(seg)
    return f"{seg // 60}:{seg % 60:02d}"


def validar_url(url):
    """Rechaza URLs hacia tu red local o internas (SSRF): un video malicioso podria
    pedirle a tu IA que abra http://192.168.x.x, localhost o servicios en la nube."""
    host = urlparse(url).hostname
    if not host:
        raise Fallo("URL invalida.")
    try:
        direcciones = {i[4][0].split("%")[0] for i in socket.getaddrinfo(host, None)}
    except socket.gaierror:
        raise Fallo(f"No se pudo resolver el dominio '{host}'.")
    for d in direcciones:
        if not ipaddress.ip_address(d).is_global:
            raise Fallo(f"Bloqueado: '{host}' apunta a una direccion privada o local ({d}). "
                        "Solo se descargan videos de internet publico.")


def descargar(url, carpeta, cookies_nav, cookies_arch):
    validar_url(url)
    cmd =[sys.executable, "-m", "yt_dlp", "--no-playlist", "--no-warnings",
           "--write-info-json", "--write-subs", "--write-auto-subs",
           "--sub-langs", "es.*,en.*,-live_chat", "--convert-subs", "srt",
           "-f", "bv*[height<=720]+ba/b[height<=720]/b",
           "--merge-output-format", "mp4",
           "-o", str(carpeta / "video.%(ext)s")]
    if not shutil.which("deno") and shutil.which("node"):
        cmd += ["--js-runtimes", "node"]
    if cookies_nav:
        cmd += ["--cookies-from-browser", cookies_nav]
    if cookies_arch:
        cmd += ["--cookies", cookies_arch]
    try:
        ejecutar(cmd + ["--", url])  # "--": nunca interpretar la URL como opcion de yt-dlp
    except Fallo as e:
        raise Fallo(f"No se pudo descargar:\n{e}\n\n{pista_de_error(str(e))}")
    videos = [p for p in carpeta.glob("video.*") if p.suffix.lower() in VIDEO]
    if not videos:
        raise Fallo("La descarga termino sin archivo de video.")
    return videos[0]


def leer_info(carpeta, url):
    crudo = carpeta / "video.info.json"
    info = {"titulo": None, "autor": None, "descripcion": None, "etiquetas": [],
            "duracion": None, "fecha": None, "url": url}
    if crudo.exists():
        d = json.loads(crudo.read_text(encoding="utf-8"))
        info.update(titulo=d.get("title"), autor=d.get("uploader") or d.get("channel"),
                    descripcion=d.get("description"), etiquetas=d.get("tags") or [],
                    duracion=d.get("duration"), fecha=d.get("upload_date"),
                    url=d.get("webpage_url") or url)
        crudo.unlink()
    return info


def srt_a_lineas(ruta):
    """Lee un .srt y devuelve [(segundos, texto)] sin repeticiones de subtitulos automaticos."""
    salida, recientes = [], []
    bloques = re.split(r"\n\s*\n", ruta.read_text(encoding="utf-8", errors="ignore"))
    for b in bloques:
        partes = b.strip().splitlines()
        i = next((k for k, l in enumerate(partes) if "-->" in l), None)
        if i is None:
            continue
        h, m, s = re.match(r"(\d+):(\d+):(\d+)", partes[i]).groups()
        t = int(h) * 3600 + int(m) * 60 + int(s)
        for linea in partes[i + 1:]:
            linea = re.sub(r"<[^>]+>", "", linea).strip()
            if linea and linea not in recientes[-4:]:
                salida.append((t, linea))
                recientes.append(linea)
    return salida


def transcribir_whisper(ruta, modelo, idioma):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise Fallo("Sin subtitulos y falta faster-whisper.\n"
                    "Instalalo:  python -m pip install faster-whisper")
    print(f"  Transcribiendo con whisper '{modelo}' "
          "(la primera vez descarga el modelo, puede tardar)...")
    wm = WhisperModel(modelo, compute_type="int8")
    segmentos, _ = wm.transcribe(str(ruta), language=idioma, vad_filter=True)
    return [(s.start, s.text.strip()) for s in segmentos if s.text.strip()]


def transcribir(ruta, carpeta, modelo, idioma, usar_subs):
    if usar_subs:
        subs = sorted(carpeta.glob("video.*.srt"))
        if subs:
            lineas = srt_a_lineas(subs[0])
            if lineas:
                return lineas, f"subtitulos de la plataforma ({subs[0].name})"
    if not tiene_audio(ruta):
        return [], "el video no tiene audio"
    return transcribir_whisper(ruta, modelo, idioma), f"whisper {modelo}"


def sacar_frames(video, carpeta, cada, maximo):
    frames = carpeta / "frames"
    frames.mkdir(exist_ok=True)
    dur = duracion(video) or 0
    paso = max(cada, dur / maximo) if dur else cada
    ejecutar(["ffmpeg", "-y", "-i", str(video), "-vf", f"fps=1/{paso},scale='min(720,iw)':-2",
              "-frames:v", str(maximo), "-q:v", "3", str(frames / "tmp_%03d.jpg")])
    nombres = []
    for i, f in enumerate(sorted(frames.glob("tmp_*.jpg"))):
        nuevo = frames / f"f_{i + 1:03d}_t{int(i * paso):02d}s.jpg"
        f.rename(nuevo)
        nombres.append((int(i * paso), nuevo.name))
    return nombres, dur


def preparar_entrada(entrada, carpeta, args):
    """Devuelve (ruta_media|None, info, subs_disponibles, es_imagen)."""
    p = Path(entrada)
    if p.exists():
        info = {"titulo": p.stem, "autor": None, "descripcion": None, "etiquetas": [],
                "duracion": None, "fecha": None, "url": None}
        ext = p.suffix.lower()
        if ext in IMAGEN:
            (carpeta / "frames").mkdir(exist_ok=True)
            shutil.copy(p, carpeta / "frames" / f"f_001_t00s{ext}")
            return None, info, False, True
        if ext in VIDEO | AUDIO:
            return p, info, False, False
        raise Fallo(f"Formato no soportado: {ext}")
    if not re.match(r"https?://", entrada):
        raise Fallo(f"No existe el archivo ni es una URL: {entrada}")
    ruta = descargar(entrada, carpeta, args.cookies_navegador, args.cookies_archivo)
    return ruta, leer_info(carpeta, entrada), True, False


def escribir_material(carpeta, info, transcripcion, origen_txt, frames, dur):
    texto = "\n".join(f"[{mmss(t)}] {x}" for t, x in transcripcion)
    (carpeta / "transcripcion.txt").write_text(texto, encoding="utf-8")
    info["duracion"] = info.get("duracion") or dur
    (carpeta / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    md = [f"# {info['titulo'] or 'Sin titulo'}", "",
          f"- Autor: {info['autor'] or 'desconocido'}",
          f"- Fuente: {info['url'] or 'archivo local'}",
          f"- Fecha: {info['fecha'] or 'desconocida'}",
          f"- Duracion: {mmss(info['duracion']) if info['duracion'] else 'desconocida'}",
          f"- Etiquetas: {', '.join(info['etiquetas'][:15]) or 'ninguna'}", ""]
    if info.get("descripcion"):
        md += ["## Descripcion del autor", "", info["descripcion"].strip(), ""]
    md += [f"## Transcripcion ({origen_txt})", "",
           texto or "(sin voz detectada: el contenido esta en las imagenes)", ""]
    md += ["## Frames (abrelos con Read, el numero tras _t es el segundo del video)", ""]
    md += [f"- frames/{n}  (~{mmss(t)})" for t, n in frames] or ["(sin frames)"]
    (carpeta / "material.md").write_text("\n".join(md), encoding="utf-8")


def procesar(entrada, carpeta, args):
    carpeta.mkdir(parents=True, exist_ok=True)
    print(f"> {entrada}")
    ruta, info, subs, es_imagen = preparar_entrada(entrada, carpeta, args)
    try:
        if es_imagen:
            frames = [(0, n.name) for n in sorted((carpeta / "frames").iterdir())]
            transcripcion, origen, dur = [], "imagen, sin audio", None
        else:
            transcripcion, origen = transcribir(ruta, carpeta, args.modelo,
                                                args.idioma, subs)
            if ruta.suffix.lower() in AUDIO:
                frames, dur = [], duracion(ruta)
            else:
                frames, dur = sacar_frames(ruta, carpeta, args.cada, args.max_frames)
        escribir_material(carpeta, info, transcripcion, origen, frames, dur)
    finally:
        for basura in carpeta.glob("video.*"):
            if basura.suffix.lower() in VIDEO | {".srt", ".json"} and not args.conservar_video:
                basura.unlink(missing_ok=True)
    palabras = sum(len(x.split()) for _, x in transcripcion)
    print(f"  listo: {palabras} palabras, {len(frames)} frames -> {carpeta / 'material.md'}")


def verificar():
    def modulo(nombre):
        try:
            __import__(nombre)
            return True
        except ImportError:
            return False
    filas = [("ffmpeg", bool(shutil.which("ffmpeg")), "winget install Gyan.FFmpeg | brew install ffmpeg | apt install ffmpeg"),
             ("ffprobe", bool(shutil.which("ffprobe")), "viene con ffmpeg"),
             ("yt-dlp", modulo("yt_dlp"), "python -m pip install yt-dlp"),
             ("faster-whisper", modulo("faster_whisper"), "python -m pip install faster-whisper"),
             ("node o deno (YouTube)", bool(shutil.which("node") or shutil.which("deno")), "opcional: https://nodejs.org")]
    ok = True
    for nombre, bien, ayuda in filas:
        print(f"  {'OK ' if bien else 'FALTA'} {nombre}" + ("" if bien else f"   -> {ayuda}"))
        ok = ok and (bien or "opcional" in ayuda)
    return 0 if ok else 1


def main():
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("entradas", nargs="*", help="URL(s) o archivo(s)")
    p.add_argument("--salida", default="video_salida")
    p.add_argument("--cada", type=float, default=2.0, help="segundos entre frames (minimo)")
    p.add_argument("--max-frames", type=int, default=20)
    p.add_argument("--modelo", default="small", help="whisper: tiny, base, small, medium")
    p.add_argument("--idioma", default=None, help="es, en... (por defecto: detectar)")
    p.add_argument("--cookies-navegador", help="chrome, firefox, edge... (solo si hace falta login)")
    p.add_argument("--cookies-archivo", help="cookies.txt exportado")
    p.add_argument("--conservar-video", action="store_true")
    p.add_argument("--verificar", action="store_true", help="revisa dependencias")
    a = p.parse_args()

    if a.verificar:
        return verificar()
    if not a.entradas:
        p.error("falta una URL o archivo")
    if not shutil.which("ffmpeg"):
        print("Falta ffmpeg. Instalalo: winget install Gyan.FFmpeg | brew install ffmpeg | apt install ffmpeg")
        return 1

    base, fallos = Path(a.salida), 0
    for i, e in enumerate(a.entradas, 1):
        destino = base if len(a.entradas) == 1 else base / f"{i:02d}"
        try:
            procesar(e, destino, a)
        except Fallo as err:
            fallos += 1
            print(f"  ERROR: {err}")
    return 1 if fallos == len(a.entradas) else 0


if __name__ == "__main__":
    sys.exit(main())
