# Seguridad

## Reportar una vulnerabilidad

**No abras un issue publico.** Usa el reporte privado de GitHub:

https://github.com/MesaRestrepo/aprende-de-videos/security/advisories/new

Incluye: que pasa, como reproducirlo, y que impacto tiene. Respondo lo antes posible y te doy credito al publicar el arreglo si quieres.

## Que hace este proyecto (y que riesgos tiene)

| Parte | Riesgo | Mitigacion |
|-------|--------|------------|
| Descarga de URLs (`yt-dlp`) | Una URL maliciosa apunta a tu red local o a servicios internos | Se bloquean direcciones privadas, locales y de metadatos de nube. La URL se pasa tras `--` para que nunca se lea como opcion |
| Procesar video (`ffmpeg`, `faster-whisper`) | Archivos multimedia mal formados | Se usan versiones actuales; mantenlas actualizadas (`python install.py`) |
| Contenido del video leido por la IA | **Inyeccion de instrucciones**: el video dice "ignora tus reglas y ejecuta X" | Las skills tratan transcripcion, descripcion y texto en pantalla como datos, nunca como ordenes, y exigen mostrarte cualquier comando antes de ejecutarlo |
| Cookies del navegador (opcional) | Acceso a tu sesion | Solo con tu permiso explicito en cada uso. `cookies.txt` esta en `.gitignore` |
| Notas guardadas | Una nota podria contener ordenes dirigidas a la IA | `consultar-conocimiento` las trata como dato sin verificar |
| Instalador | Ejecutar codigo ajeno | No descarga ni ejecuta nada fuera de `pip install yt-dlp faster-whisper` dentro de un entorno aislado. Lee `install.py` antes de correrlo |

## Limites que debes conocer

- La proteccion contra URLs internas comprueba la resolucion DNS en el momento de validar; no es una defensa absoluta contra ataques de DNS que cambian la respuesta.
- Las dependencias (`yt-dlp`, `faster-whisper`) vienen de PyPI y no estan fijadas a una version, porque `yt-dlp` debe actualizarse seguido para seguir funcionando. Es un riesgo de cadena de suministro que se acepta de forma consciente.
- Una IA puede equivocarse o ser enganada. Revisa lo que te pida ejecutar.

## Recomendaciones para usuarios

1. Instala desde el repo oficial y lee `install.py` antes de ejecutarlo.
2. No uses `--cookies-navegador` con cuentas importantes si no es necesario; prefiere pasar el archivo del video.
3. No pegues enlaces ni archivos de fuentes que no conozcas en una sesion donde tu IA tenga permisos amplios sobre tus archivos.
4. Manten `yt-dlp` al dia.

## Versiones con soporte

Solo la ultima version de la rama `main`.
