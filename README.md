# ThinkPad Dolby en EasyEffects

Perfiles de [EasyEffects](https://github.com/wwmm/easyeffects) que emulan el realce **Dolby
Audio / Dolby Atmos** que Lenovo trae en Windows, aplicado a los parlantes internos y a la
salida de auriculares de una ThinkPad.

No reproduce el procesamiento propietario (no hay virtualización ni licencias Dolby): reproduce
su comportamiento audible — curva en V suave, realce sicofísico de graves, presencia para voz,
brillo, nivelación de volumen y protección de excursión de los drivers.

Probado en **ThinkPad E14 Gen 2** (Realtek ALC257) con Ubuntu 26.04, PipeWire 1.6.2 y
EasyEffects 8.1.2. Debería funcionar en cualquier ThinkPad con parlantes estéreo internos y jack
de 3.5 mm.

## Instalación (sistema limpio)

```bash
sudo apt install easyeffects    # si todavía no está
git clone https://github.com/luismasuarez/thinkpad-dolby-easyeffects.git
cd thinkpad-dolby-easyeffects
./install.sh
```

El instalador:

1. copia los dos perfiles a `~/.local/share/easyeffects/output/`;
2. detecta el sink analógico y las rutas `speaker` / `headphones` en PipeWire (las descripciones
   están traducidas, así que se resuelven en el momento) y crea los archivos de autoload;
3. reinicia EasyEffects y muestra qué perfil quedó cargado.

Opciones: `--dry-run`, `--no-restart`, `--uninstall`.

## Qué queda configurado

| Archivo | Contenido |
| --- | --- |
| `output/Dolby-ThinkPad-Speakers.json` | Perfil para parlantes internos |
| `output/Dolby-ThinkPad-Headphones.json` | Perfil para el jack de 3.5 mm |
| `autoload/output/<sink>:<ruta>.json` | Carga automática según la ruta activa (parlantes o auriculares) |

El autoload hace que el perfil correcto se aplique solo: al desenchufar los auriculares entra el
de parlantes y al enchufarlos entra el de auriculares, sin tocar nada.

### Cadena de parlantes

| Orden | Plugin | Función |
| --- | --- | --- |
| 1 | `filter` | Paso alto 60 Hz, 24 dB/oct |
| 2 | `equalizer` | +2.5 dB @160 Hz, −2 dB @550 Hz, +3 dB @2.7 kHz, +2.5 dB @7 kHz, salida −3 dB |
| 3 | `bass_enhancer` | Armónicos bajo 150 Hz (amount 2.5, harmonics 9) |
| 4 | `exciter` | Armónicos desde 6.5 kHz (amount 2.5) |
| 5 | `autogain` | Nivelación de volumen, objetivo −16 LUFS |
| 6 | `stereo_tools` | Ensanchado leve (stereo base 0.15) |
| 7 | `limiter` | Techo −1 dBFS |

### Cadena de auriculares

`filter` (paso alto 25 Hz) → `equalizer` (graves suaves, +1.5 dB @3.2 kHz, +1.5 dB @8 kHz) →
`crossfeed` (fcut 700, feed 4.5) → `limiter` (−1.5 dBFS).

## Ajustes

Abre `easyeffects`, pestaña de efectos de **salida**. Lo que más se nota:

| Quiero | Tocar |
| --- | --- |
| Más o menos graves | `equalizer` banda 1 (shelf 160 Hz) y `bass_enhancer` → Amount |
| Más o menos brillo | `equalizer` banda 4 (shelf 7 kHz) y `exciter` → Amount |
| Volumen más parejo / menos comprimido | `autogain` → Target (o desactivarlo) |
| Sacar el sonido "de la cabeza" en auriculares | `crossfeed` → Feed (4 a 9) |

Guarda el perfil con el mismo nombre para conservar los cambios. Si editas los JSON a mano,
regenera desde el generador: `python3 tools/gen_presets.py` (los JSON del repo son la salida de
ese script).

## Verificación

`tools/measure_response.py` mide la respuesta real de la cadena: reproduce un tono por frecuencia
dentro del sink de EasyEffects y graba el monitor del sink de hardware, leyendo la magnitud en la
fundamental. Se corre una vez con el perfil y otra con `Nothing` para restar.

Curva medida en la ThinkPad E14 Gen 2, normalizada a 1 kHz (sin las etapas de dinámica):

| 125 Hz | 250 Hz | 500 Hz | 2 kHz | 4 kHz | 8 kHz |
| --- | --- | --- | --- | --- | --- |
| +4.3 dB | −0.6 dB | −1.2 dB | +2.1 dB | +1.7 dB | +2.3 dB |

## Notas

- **El `Hi-pass` del `equalizer` de LSP no sirve**: recalcula la Q por etapa y termina con una
  resonancia de ~+30 dB en la frecuencia de corte (medido). Por eso el paso alto va en el plugin
  `filter`.
- `autogain` baja el nivel de contenido masterizado muy fuerte; si prefieres dinámica, desactívalo.
- El autoload se indexa por la **descripción** de la ruta, que PipeWire traduce. Si cambias el
  idioma del sistema, vuelve a ejecutar `./install.sh` para regenerar esos archivos.
- Los perfiles asumen parlantes estéreo internos. En un equipo con otra geometría (por ejemplo
  Thunderbolt/USB) conviene ajustar la banda de 160 Hz a oído.
