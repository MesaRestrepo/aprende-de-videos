#!/usr/bin/env python3
"""Instala (o actualiza) aprende-de-videos para Claude Code. Windows, macOS y Linux.

    python install.py                  instalar / actualizar
    python install.py --desinstalar    quitar skills y programa (tus notas NO se borran)
    python install.py --skills-dir D   instalar las skills en otra carpeta (otras IAs)
"""
import argparse
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SKILLS = ["aprender-de-video", "consultar-conocimiento"]
DEPS = ["yt-dlp", "faster-whisper"]


def salir(msg):
    print(f"\nERROR: {msg}")
    sys.exit(1)


def python_de(venv_dir):
    return venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def instalar_skill(origen, destino, reemplazos):
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(origen, destino)
    for md in destino.rglob("*.md"):
        texto = md.read_text(encoding="utf-8")
        for k, v in reemplazos.items():
            texto = texto.replace(k, v)
        md.write_text(texto, encoding="utf-8")


def main():
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--claude-home", help="por defecto ~/.claude (o variable CLAUDE_HOME)")
    p.add_argument("--skills-dir", help="carpeta de skills (por defecto <claude-home>/skills)")
    p.add_argument("--desinstalar", action="store_true")
    a = p.parse_args()

    home = Path(a.claude_home or os.environ.get("CLAUDE_HOME") or Path.home() / ".claude")
    skills_dir = Path(a.skills_dir) if a.skills_dir else home / "skills"
    raiz = home / "aprende-de-videos"

    if a.desinstalar:
        for s in SKILLS:
            shutil.rmtree(skills_dir / s, ignore_errors=True)
        shutil.rmtree(raiz, ignore_errors=True)
        print(f"Desinstalado. Tus notas siguen en {home / 'conocimiento'} (borralas a mano si quieres).")
        return

    if sys.version_info < (3, 9):
        salir("Se necesita Python 3.9 o superior.")

    print("1/4 Entorno de Python aislado...")
    vdir = raiz / "venv"
    if not python_de(vdir).exists():
        try:
            venv.EnvBuilder(with_pip=True, clear=True).create(vdir)
        except Exception as e:
            salir(f"No se pudo crear el entorno ({e}).\n"
                  "En Linux: sudo apt install python3-venv. En otros casos usa un Python oficial de python.org.")
    py = python_de(vdir)

    print("2/4 Dependencias (yt-dlp, faster-whisper; la primera vez pesa ~200 MB)...")
    r = subprocess.run([str(py), "-m", "pip", "install", "-q", "-U", *DEPS])
    if r.returncode != 0:
        salir("pip fallo. Si el error menciona 'ctranslate2' o 'onnxruntime', tu Python es muy nuevo: "
              "usa Python 3.10 a 3.12 y repite.")

    print("3/4 Programas y skills...")
    (raiz / "scripts").mkdir(parents=True, exist_ok=True)
    for f in (AQUI / "scripts").glob("*.py"):
        shutil.copy(f, raiz / "scripts" / f.name)
    reemplazos = {"{{PYTHON}}": py.as_posix(), "{{SCRIPTS}}": (raiz / "scripts").as_posix()}
    skills_dir.mkdir(parents=True, exist_ok=True)
    for s in SKILLS:
        instalar_skill(AQUI / "skills" / s, skills_dir / s, reemplazos)

    print("4/4 Verificando...")
    v = subprocess.run([str(py), str(raiz / "scripts" / "procesar_video.py"), "--verificar"])

    print(f"\nSkills en: {skills_dir}\nNotas en:  {home / 'conocimiento'}")
    if v.returncode != 0:
        print("\nFalta algo de la lista de arriba (casi siempre ffmpeg). Instalalo y repite 'python install.py'.")
        sys.exit(1)
    print("\nListo. Reinicia tu IA y pega un enlace de video.")


if __name__ == "__main__":
    main()
