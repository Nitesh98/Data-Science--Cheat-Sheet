#!/usr/bin/env python3
"""
Build a reel into an Instagram-ready MP4 (1080x1920, 30 fps, H.264 + AAC) and a cover PNG.

    python3 build.py 01-simpsons-paradox              # video + cover
    python3 build.py 01-simpsons-paradox --check      # quick contact sheet only, no video

Needs: node + playwright + chromium (already in this environment) and `pip install imageio-ffmpeg`
for an ffmpeg with H.264. Frames go to a temp folder, never into the repo.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "engine"))
import sfx  # noqa: E402


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("Install an H.264-capable ffmpeg first:  pip install imageio-ffmpeg")


def node(*args):
    subprocess.run(["node", str(HERE / "engine" / "render.mjs"), *map(str, args)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reel")
    ap.add_argument("--check", action="store_true", help="render a contact sheet of key moments only")
    ap.add_argument("--times", default="", help="comma-separated seconds for --check")
    ap.add_argument("--workers", type=int, default=4)
    opts = ap.parse_args()

    folder = HERE / opts.reel
    page, out = folder / "reel.html", folder / "out"
    out.mkdir(exist_ok=True)
    ff = ffmpeg()
    work = Path(tempfile.mkdtemp(prefix="reel-"))
    try:
        if opts.check:
            times = opts.times or "0.6,1.6,2.8,4.6,6.0,8.2,10.6,12.0,13.5,16.0,18.5,21.5"
            node("stills", page, work, times)
            sheet = out / "contact-sheet.png"
            subprocess.run([ff, "-y", "-loglevel", "error", "-pattern_type", "glob", "-i", str(work / "still_*.png"),
                            "-vf", "scale=270:-1,tile=6x2:padding=6:color=black", "-frames:v", "1", str(sheet)], check=True)
            print("contact sheet:", sheet)
            return

        print("1/4  rendering frames")
        node("frames", page, work, 30, opts.workers)
        meta = json.loads((work / "meta.json").read_text())
        print("2/4  synthesizing sound effects")
        sfx.render(meta["cues"], meta["duration"], str(work / "sfx.wav"))
        print("3/4  encoding MP4")
        mp4 = out / f"{opts.reel}.mp4"
        subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", "30", "-i", str(work / "f%05d.png"),
                        "-i", str(work / "sfx.wav"), "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1", "-r", "30",
                        "-c:a", "aac", "-b:a", "192k", "-t", str(meta["duration"]), "-movflags", "+faststart", str(mp4)],
                       check=True)
        print("4/4  rendering cover")
        if (folder / "cover.html").exists():
            node("shot", folder / "cover.html", out / "cover.png")
        print(f"done: {mp4}  ({mp4.stat().st_size / 1e6:.1f} MB)")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
