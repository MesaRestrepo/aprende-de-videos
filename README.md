# aprende-de-videos

Haz que tu IA **aprenda de Reels, TikToks, YouTube Shorts, videos, audios y capturas**, y que **recuerde lo aprendido**.

Pegas un enlace (o un archivo). La IA lo escucha, mira sus imagenes, extrae lo importante y lo guarda en una base de conocimiento tuya. Despues, cualquier conversacion puede consultarla.

```
Tu:  aprende de este tiktok https://www.tiktok.com/@user/video/123
IA:  Aprendi: como hacer X en 4 pasos. Guardado en  cocina/pan-sin-horno.

(dias despues)
Tu:  como era lo del pan sin horno?
IA:  Segun tu nota cocina/pan-sin-horno (fuente: @user)...
```

## Que incluye

| Skill | Que hace |
|-------|----------|
| `aprender-de-video` | Descarga o lee el video, transcribe la voz, extrae imagenes, escribe una nota y la guarda. |
| `consultar-conocimiento` | Busca en tus notas antes de responder y cita la fuente. |

Y dos programas que usan las skills:

- `procesar_video.py`: URL o archivo -> `material.md` con datos, transcripcion con tiempos e imagenes.
- `conocimiento.py`: guardar, buscar, listar, ver y borrar notas (Markdown plano, tuyas, en tu disco).

## Instalar

Necesitas **Python 3.10 o superior** (probado en 3.11) y **[ffmpeg](https://ffmpeg.org/download.html)**.

```bash
# 1. ffmpeg (una vez)
winget install Gyan.FFmpeg        # Windows
brew install ffmpeg               # macOS
sudo apt install ffmpeg           # Linux

# 2. instalar
git clone https://github.com/MesaRestrepo/aprende-de-videos
cd aprende-de-videos
python install.py
```

El instalador crea un entorno propio (no ensucia tu Python), instala `yt-dlp` y `faster-whisper`, copia las skills a `~/.claude/skills` y verifica todo. Reinicia tu IA.

Actualizar: `git pull` y `python install.py` otra vez. Quitar: `python install.py --desinstalar` (tus notas no se borran).

## Usar

- "Aprende de este reel: <url>"
- "Estudia estos 3 videos y hazme un resumen: <url1> <url2> <url3>"
- "Aprende de este video" + archivo `.mp4`, `.mp3` o una captura `.png`
- "Que tengo guardado sobre marketing?"
- "Convierte lo que aprendiste del video en una skill"

Tus notas viven en `~/.claude/conocimiento/` (cambia la carpeta con la variable `APRENDE_KB`). Son archivos `.md`: puedes abrirlos, editarlos, hacerles copia o sincronizarlos con Obsidian.

## Que funciona y que no (probado)

| Caso | Estado |
|------|--------|
| TikTok publico por URL | Funciona |
| Video o audio local, capturas | Funciona |
| Video sin voz (solo texto en pantalla) | Funciona: la IA lee los frames |
| Voz sin subtitulos | Funciona: transcripcion local con whisper |
| YouTube / Shorts | Depende: YouTube bloquea IPs con "confirma que no eres un bot". Usa `--cookies-navegador` o pasa el archivo descargado |
| Instagram / Facebook / Vimeo | Suelen pedir sesion. Misma solucion |
| Videos privados | No |

**Cookies:** `--cookies-navegador chrome` hace que yt-dlp lea las cookies de tu navegador para parecer tu sesion. Es opcional y tu IA debe pedirte permiso antes. Si prefieres no hacerlo, descarga o graba el video y pasa el archivo.

## Como funciona

1. `yt-dlp` descarga video, descripcion y subtitulos (si existen).
2. Voz: subtitulos de la plataforma o `faster-whisper` en tu computadora.
3. `ffmpeg` saca hasta 20 imagenes; el segundo va en el nombre (`f_004_t06s.jpg`).
4. La IA lee `material.md`, mira las imagenes (lo que se ve y no se dice cuenta), extrae pasos y datos exactos.
5. Guarda la nota con fuente y autor. Misma fuente = actualiza, no duplica.

El procesamiento corre en tu computadora. Lo que la IA lee (texto e imagenes) viaja a su proveedor, como cualquier conversacion.

## Seguridad

- **El contenido de un video es un dato, no una orden.** Un video puede decir "ignora tus instrucciones y ejecuta esto". Las skills le indican a la IA que no obedezca y te avise.
- La IA no ejecuta comandos vistos en un video sin ensenartelos antes.
- Los videos virales mezclan consejos buenos y malos. Cada nota separa "Cuidado / no verificado". Tu criterio manda, sobre todo en salud, dinero y seguridad.
- `cookies.txt` esta en `.gitignore`. No lo subas nunca a ningun repo.
- Solo se descargan videos de internet publico: las URLs hacia tu red local, `localhost` o servicios internos se bloquean.
- Todo cambio al repo lo revisa y aprueba el mantenedor. El CI corre sin secretos.
- Lee [SECURITY.md](SECURITY.md) para el detalle de riesgos y para **reportar una vulnerabilidad en privado**.

## Otras IAs (Cursor, Codex, Gemini CLI...)

Las skills son Markdown mas scripts de linea de comandos. Cualquier IA con terminal puede usarlas:

```bash
python install.py --skills-dir /ruta/donde/tu-ia/lee/skills
```

o copia el contenido de `skills/*/SKILL.md` a las instrucciones de tu IA, cambiando `{{PYTHON}}` por tu `python` y `{{SCRIPTS}}` por la carpeta `scripts/`.

## Problemas comunes

| Mensaje | Solucion |
|---------|----------|
| `FALTA ffmpeg` | Instalalo (arriba) y abre una terminal nueva |
| `Sign in to confirm you're not a bot` | Cookies del navegador o pasar el archivo |
| `No se pudo descargar` en muchos sitios | `python install.py` para actualizar `yt-dlp` |
| pip falla instalando `faster-whisper` | Usa Python 3.11 (el probado); versiones muy nuevas pueden no tener paquetes aun |
| Transcripcion mala | `--modelo medium` (mas lento) y `--idioma es` |

Comprobar la instalacion: `python tests/smoke.py`.

## Etica

Para aprender, no para copiar y republicar. Cita al autor. Respeta los terminos de cada plataforma y los derechos de autor: las notas guardan lo aprendido en tus palabras, no el video.

## Contribuir

Tu ayuda en el codigo es bienvenida: deteccion de cambio de escena, OCR, mas idiomas, soporte probado para otras IAs, mas pruebas.

1. Haz fork y crea una rama.
2. `python tests/smoke.py` debe pasar.
3. Abre un Pull Request.

Guia completa y reglas de seguridad: [CONTRIBUTING.md](CONTRIBUTING.md). Abre un issue antes de cambios grandes.

## Licencia

MIT
