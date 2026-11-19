#!/usr/bin/env python3
"""Une todos los audios de una carpeta en un único archivo, uno tras otro.

Requiere ffmpeg instalado y accesible en el PATH.

Uso:
    python unir_audios.py CARPETA
    python unir_audios.py CARPETA -o resultado.mp3
    python unir_audios.py CARPETA -o resultado.wav --recursivo
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXTENSIONES = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma"}


def orden_natural(ruta: Path):
    """Ordena 'audio2' antes que 'audio10'."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", ruta.name)]


def main():
    ap = argparse.ArgumentParser(description="Une los audios de una carpeta en uno solo.")
    ap.add_argument("carpeta", type=Path, help="Carpeta con los audios")
    ap.add_argument("-o", "--salida", type=Path, default=Path("unido.mp3"),
                    help="Archivo de salida (el formato se deduce de la extensión)")
    ap.add_argument("-r", "--recursivo", action="store_true", help="Incluir subcarpetas")
    ap.add_argument("--frecuencia", type=int, default=44100, help="Frecuencia de muestreo (Hz)")
    ap.add_argument("--canales", choices=["mono", "stereo"], default="stereo")
    args = ap.parse_args()

    if shutil.which("ffmpeg") is None:
        sys.exit("Error: ffmpeg no está instalado o no está en el PATH.")
    if not args.carpeta.is_dir():
        sys.exit(f"Error: '{args.carpeta}' no es una carpeta.")

    salida = args.salida.resolve()
    patron = args.carpeta.rglob("*") if args.recursivo else args.carpeta.glob("*")
    archivos = sorted(
        (p for p in patron
         if p.is_file() and p.suffix.lower() in EXTENSIONES and p.resolve() != salida),
        key=orden_natural,
    )

    if not archivos:
        sys.exit("No se encontraron archivos de audio en la carpeta.")

    print(f"Uniendo {len(archivos)} archivos:")
    for a in archivos:
        print(f"  - {a.name}")

    # Normaliza cada entrada al mismo formato y las concatena con el filtro concat,
    # así funciona aunque los archivos tengan distinto formato, canales o frecuencia.
    partes = []
    for i in range(len(archivos)):
        partes.append(
            f"[{i}:a]aformat=sample_rates={args.frecuencia}:channel_layouts={args.canales}[a{i}]"
        )
    etiquetas = "".join(f"[a{i}]" for i in range(len(archivos)))
    partes.append(f"{etiquetas}concat=n={len(archivos)}:v=0:a=1[out]")
    filtro = ";\n".join(partes)

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(filtro)
        script_filtro = f.name

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats"]
    for a in archivos:
        cmd += ["-i", str(a)]
    cmd += ["-filter_complex_script", script_filtro, "-map", "[out]", "-vn", str(salida)]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        sys.exit("Error: ffmpeg falló al unir los archivos.")
    finally:
        Path(script_filtro).unlink(missing_ok=True)

    print(f"\nListo: {salida}")


if __name__ == "__main__":
    main()
