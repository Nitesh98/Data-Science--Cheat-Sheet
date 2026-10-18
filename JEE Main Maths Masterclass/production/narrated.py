"""NarratedScene: a Manim Scene whose timing is driven by recorded narration.

Scene code is written as beats:

    self.say("sentence one | sentence two", Create(graph), sfx="move")

* text is split on "|" into caption chunks; each chunk is synthesized
  separately so caption timings are exact, not estimated;
* the animations start with the narration, and the scene holds until the
  narration has finished (plus `hold` seconds of reading time);
* every narration clip, sound cue, section marker and "dense reasoning" span
  is logged to a timeline JSON, from which audio_mix.py builds the soundtrack,
  captions.py builds SRT/VTT, and the cue sheet / timestamps are generated.
"""
import json, os
from manim import *
import config as C
import style as S
import tts


class NarratedScene(Scene):
    CHAPTER = "C00"
    CHAPTER_TITLE = ""
    SECTION = ""
    SECTION_TITLE = ""

    def setup(self):
        self.timeline = {"chapter": self.CHAPTER, "section": self.SECTION, "fps": config.frame_rate,
                         "events": []}
        self._chrome = None

    # ---- time & logging ---------------------------------------------------
    @property
    def now(self):
        return float(self.renderer.time)

    def log(self, kind, **kw):
        self.timeline["events"].append({"t": round(self.now, 3), "kind": kind, **kw})

    def mark(self, section_id, title):
        """Navigation marker -> chapter timestamps and coverage matrix."""
        self.log("section", id=section_id, title=title)

    def cue(self, name, gain_db=0.0):
        """Sound-design cue at the current time (see audio_mix.SFX)."""
        self.log("sfx", name=name, gain_db=gain_db)

    def music(self, state):
        """Music state: 'on' | 'low' | 'off' (dense reasoning / before a correction)."""
        self.log("music", state=state)

    # ---- chrome ------------------------------------------------------------
    def chrome(self, section_title=None):
        if self._chrome is not None:
            self.remove(self._chrome)
        self._chrome = VGroup(S.header(self.CHAPTER, self.CHAPTER_TITLE,
                                       section_title or self.SECTION_TITLE),
                              S.progress_bar(self.CHAPTER))
        self.add(self._chrome)
        return self._chrome

    # ---- the core beat -------------------------------------------------------
    def say(self, text, *anims, run_time=None, hold=0.5, sfx=None, dense=False, lag=0.0):
        chunks = [c.strip() for c in text.split("|") if c.strip()]
        clips = [tts.synth(c) for c in chunks]
        if sfx:
            self.cue(sfx)
        if dense:
            self.music("off")
        start = self.now + lag
        t = start
        for c in clips:
            self.timeline["events"].append({"t": round(t, 3), "kind": "voice", "path": c.path,
                                            "dur": round(c.dur, 3), "text": c.text})
            t += c.dur + C.SENTENCE_GAP
        total = (t - C.SENTENCE_GAP - self.now) if clips else 0.0
        if anims:
            rt = run_time if run_time is not None else min(max(1.0, 0.6 * total), 3.0)
            self.play(*anims, run_time=rt)
            remaining = total + hold - rt
        else:
            remaining = total + hold
        if remaining > 1 / config.frame_rate:
            self.wait(remaining)
        if dense:
            self.music("on")

    def think(self, seconds, label="PAUSE & PREDICT", where=None):
        """Genuine retrieval pause with a visible countdown and quiet anticipation."""
        cd = S.countdown(seconds, label)
        cd.move_to(where if where is not None else DOWN * 3.1 + RIGHT * 4.6)
        self.music("low")
        self.cue("anticipate")
        self.add(cd)
        self.play(cd.vt.animate.set_value(1), run_time=seconds, rate_func=linear)
        self.remove(cd)
        self.music("on")

    def tear_down(self):
        out = os.path.join(C.RENDERS, "timelines")
        os.makedirs(out, exist_ok=True)
        self.timeline["duration"] = round(self.now, 3)
        with open(os.path.join(out, f"{type(self).__name__}.json"), "w") as f:
            json.dump(self.timeline, f, indent=1, ensure_ascii=False)
