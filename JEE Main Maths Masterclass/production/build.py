"""Render one scene end-to-end and validate it.

usage: /opt/mvenv/bin/python production/build.py scenes/c01_7_transformations.py C01_7_Transformations [--preview]

Steps: manim render (native 3840x2160@30 unless --preview) -> soundtrack from
the narration timeline -> mux -> 1080p viewing copy -> SRT/VTT captions ->
cue sheet -> automated checks (resolution, fps, duration, audio stream,
loudness, black frames, frozen frames) written to a JSON report.
"""
import glob, json, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import config as C
import audio_mix, captions


def run(cmd, **kw):
    print("+", " ".join(cmd)[:200], flush=True)
    return subprocess.run(cmd, check=True, **kw)


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels:format=duration",
                        "-of", "json", path], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def detect(path, filt, key):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vf", filt, "-an", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return [l.strip() for l in r.splitlines() if key in l]


def main(scene_file, scene, preview=False):
    env = dict(os.environ, JEE_PREVIEW="1" if preview else "0", PYTHONPATH=HERE)
    media = os.path.join(C.RENDERS, "media")
    run(["/opt/mvenv/bin/manim", "render", "--disable_caching", "--media_dir", media, "-o", scene,
         os.path.join(HERE, scene_file), scene], env=env, cwd=HERE)
    vids = sorted(glob.glob(os.path.join(media, "videos", "*", "*", scene + ".mp4")), key=os.path.getmtime)
    silent = vids[-1]
    tag = "preview" if preview else "4k"
    out_dir = os.path.join(C.RENDERS, "chapters", scene)
    os.makedirs(out_dir, exist_ok=True)
    tl_path = os.path.join(C.RENDERS, "timelines", scene + ".json")
    shutil.copy(tl_path, os.path.join(out_dir, scene + ".timeline.json"))
    tl = json.load(open(tl_path))
    wav = os.path.join(out_dir, scene + ".mix.wav")
    audio_mix.build(tl_path, wav)
    final = os.path.join(out_dir, f"{scene}_{tag}.mp4")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", silent, "-i", wav,
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k",
         "-shortest", "-movflags", "+faststart", final])
    if not preview:
        hd = os.path.join(out_dir, f"{scene}_1080p.mp4")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", final, "-vf",
             "scale=1920:1080:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
             "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", hd])
    cs = captions.cues(tl["events"])
    captions.write_srt(cs, os.path.join(out_dir, scene + ".hinglish.srt"))
    captions.write_vtt(cs, os.path.join(out_dir, scene + ".hinglish.vtt"))
    captions.cue_sheet(tl["events"], os.path.join(out_dir, scene + ".cuesheet.md"), title=scene)
    # ---- automated QA
    p = probe(final)
    I, TP = audio_mix.measure(final)
    black = detect(final, "blackdetect=d=0.5:pix_th=0.05", "black_start")
    frozen = detect(final, "freezedetect=n=0.001:d=25", "freeze_start")  # >25 s static = suspicious
    v = next(s for s in p["streams"] if s["codec_type"] == "video")
    a = [s for s in p["streams"] if s["codec_type"] == "audio"]
    report = {
        "file": final, "width": v["width"], "height": v["height"], "fps": v["r_frame_rate"],
        "duration_s": float(p["format"]["duration"]), "timeline_duration_s": tl["duration"],
        "audio_streams": len(a), "audio": a, "integrated_lufs": I, "true_peak_dbtp": TP,
        "black_segments": black, "long_static_segments": frozen,
        "voice_clips": sum(e["kind"] == "voice" for e in tl["events"]),
        "sections": [e for e in tl["events"] if e["kind"] == "section"],
        "tts_backend": C.TTS_BACKEND,
        "pass": {
            "resolution": (v["width"], v["height"]) == ((1280, 720) if preview else (C.WIDTH, C.HEIGHT)),
            "fps": v["r_frame_rate"] == (f"{15}/1" if preview else f"{C.FPS}/1"),
            "audio": len(a) == 1,
            "duration_match": abs(float(p["format"]["duration"]) - tl["duration"]) < 0.5,
            "loudness": abs(I - C.TARGET_LUFS) <= 1.0 and TP <= C.TARGET_TP + 0.05,
            "no_black": not black,
        },
    }
    json.dump(report, open(os.path.join(out_dir, f"{scene}_{tag}.qa.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(report["pass"]), I, TP, report["duration_s"])
    return report


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--preview" in sys.argv)
