#!/usr/bin/env python3
"""Prueba de humo sin red ni whisper: video local sin audio, imagen y base de conocimiento.

    python tests/smoke.py        (necesita ffmpeg en el PATH)
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "scripts" / "procesar_video.py"
KB = RAIZ / "scripts" / "conocimiento.py"


def correr(*cmd, entrada=None):
    r = subprocess.run([sys.executable, *map(str, cmd)], capture_output=True, text=True,
                       encoding="utf-8", input=entrada)
    assert r.returncode == 0, f"fallo {cmd}:\n{r.stdout}\n{r.stderr}"
    return r.stdout


def main():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        video, imagen = t / "demo.mp4", t / "captura.png"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc=duration=6:size=320x240:rate=10", "-pix_fmt", "yuv420p",
                        str(video)], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc=size=320x240:rate=1", "-frames:v", "1", str(imagen)], check=True)

        # 1. video local sin audio + imagen en una sola llamada
        salida = t / "out"
        correr(PROC, video, imagen, "--salida", salida)
        md = (salida / "01" / "material.md").read_text(encoding="utf-8")
        assert "el video no tiene audio" in md and "frames/f_001" in md
        assert len(list((salida / "01" / "frames").glob("*.jpg"))) >= 2
        assert list((salida / "02" / "frames").glob("f_001_t00s.png"))
        json.loads((salida / "01" / "info.json").read_text(encoding="utf-8"))

        # 2. base de conocimiento: guardar, actualizar sin duplicar, buscar con acentos, borrar
        kb = t / "kb"
        base = [KB, "--kb", kb]
        correr(*base, "guardar", "--titulo", "Centrar un div", "--tema", "CSS",
               "--etiquetas", "css", "--fuente", "https://x/1", "--autor", "ana",
               entrada="Usar display flex.\n")
        correr(*base, "guardar", "--titulo", "Centrar un div", "--tema", "CSS",
               "--fuente", "https://x/1", entrada="Usar display flex o grid.\n")
        assert len(list(kb.rglob("*.md"))) == 2, "debe haber 1 nota + INDICE"
        assert "ana" in correr(*base, "ver", "css/centrar-un-div")  # conserva autor
        assert "centrar-un-div" in correr(*base, "buscar", "cómo centrár")
        assert "Sin resultados" in correr(*base, "buscar", "pizza napolitana")
        correr(*base, "borrar", "css/centrar-un-div")
        assert "0 notas" in correr(*base, "listar")
    print("OK: todo paso")


if __name__ == "__main__":
    main()
