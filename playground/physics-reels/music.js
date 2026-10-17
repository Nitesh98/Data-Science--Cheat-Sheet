/*
 * Original calm ambient background music, synthesised in the browser (Web Audio). Copyright-free:
 * nothing is sampled, so there is no Content ID risk. Deterministic: the same seed and length give the
 * same track. Each reel's seed (its day number by default) picks the key, the chord progression
 * and the arpeggio pattern, so every reel sounds related but not identical.
 *
 *   const buf = await window.music.render(seconds, seed)   // AudioBuffer (stereo, 48 kHz)
 *   const b64 = await window.music.encode(buf)             // Opus-in-WebM, base64 (records in real time)
 */
(() => {
  const SR = 48000;
  const KEYS = [48, 50, 51, 53, 55, 57];                 // C D Eb F G A (as MIDI roots, octave 3)
  // calm progressions as [root offset, chord tones...] in semitones above the key
  const PROGRESSIONS = [
    [[0, 4, 7, 11], [9, 12, 16, 19], [5, 9, 12, 16], [7, 11, 14, 17]],      // Imaj7  vi7  IVmaj7  V6
    [[9, 12, 16, 19], [5, 9, 12, 16], [0, 4, 7, 11], [7, 11, 14, 19]],      // vi7  IVmaj7  Imaj7  Vsus
    [[5, 9, 12, 16], [4, 7, 11, 14], [2, 5, 9, 12], [0, 4, 7, 11]],         // IVmaj7  iii7  ii7  Imaj7
  ];
  const hz = (m) => 440 * Math.pow(2, (m - 69) / 12);
  function rng(seed) {
    let a = (Math.imul(seed + 7, 2654435761) ^ 0x51ed270b) >>> 0;
    return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }

  async function render(seconds, seed = 1, { volume = 0.8 } = {}) {
    const r = rng(seed);
    const key = KEYS[Math.floor(r() * KEYS.length)];
    const prog = PROGRESSIONS[Math.floor(r() * PROGRESSIONS.length)];
    const bpm = 66 + Math.floor(r() * 10), beat = 60 / bpm, bar = beat * 4;
    const ctx = new OfflineAudioContext(2, Math.ceil(seconds * SR), SR);

    // master: gentle compression, slow fade in and out
    const master = ctx.createGain();
    master.gain.setValueAtTime(0, 0);
    master.gain.linearRampToValueAtTime(volume, 1.8);
    master.gain.setValueAtTime(volume, Math.max(1.9, seconds - 2.5));
    master.gain.linearRampToValueAtTime(0, seconds);
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -20; comp.ratio.value = 3; comp.attack.value = 0.02; comp.release.value = 0.4;
    master.connect(comp).connect(ctx.destination);

    // reverb from a seeded, decaying stereo noise impulse
    const ir = ctx.createBuffer(2, SR * 4, SR);
    for (let ch = 0; ch < 2; ch++) {
      const d = ir.getChannelData(ch), n = rng(seed * 31 + ch);
      for (let i = 0; i < d.length; i++) d[i] = (n() * 2 - 1) * Math.pow(1 - i / d.length, 3.2);
    }
    const verb = ctx.createConvolver(); verb.buffer = ir;
    const wet = ctx.createGain(); wet.gain.value = 0.55; verb.connect(wet).connect(master);
    const dry = ctx.createGain(); dry.gain.value = 0.75; dry.connect(master);

    // soft echo for the plucks
    const delay = ctx.createDelay(2); delay.delayTime.value = beat * 0.75;
    const fb = ctx.createGain(); fb.gain.value = 0.32;
    const dl = ctx.createBiquadFilter(); dl.type = "lowpass"; dl.frequency.value = 2400;
    delay.connect(dl).connect(fb).connect(delay); dl.connect(verb);

    const padBus = ctx.createBiquadFilter(); padBus.type = "lowpass"; padBus.frequency.value = 1100; padBus.Q.value = 0.3;
    const padGain = ctx.createGain(); padGain.gain.value = 0.09; padBus.connect(padGain); padGain.connect(dry); padGain.connect(verb);

    const nBars = Math.ceil(seconds / bar) + 1;
    for (let b = 0; b < nBars; b++) {
      const t0 = b * bar, chord = prog[b % prog.length];
      // pad: two detuned triangles per chord tone, slow swell
      for (const semi of chord.slice(1)) {
        for (const det of [-7, 7]) {
          const o = ctx.createOscillator(); o.type = "triangle"; o.frequency.value = hz(key + 12 + semi); o.detune.value = det;
          const g = ctx.createGain(); g.gain.setValueAtTime(0, t0);
          g.gain.linearRampToValueAtTime(1, t0 + bar * 0.45); g.gain.linearRampToValueAtTime(0.0001, t0 + bar * 1.25);
          o.connect(g).connect(padBus); o.start(t0); o.stop(t0 + bar * 1.3);
        }
      }
      // bass: soft sine on the chord root
      const bo = ctx.createOscillator(); bo.type = "sine"; bo.frequency.value = hz(key - 12 + chord[0]);
      const bg = ctx.createGain(); bg.gain.setValueAtTime(0, t0); bg.gain.linearRampToValueAtTime(0.16, t0 + 0.35);
      bg.gain.exponentialRampToValueAtTime(0.0001, t0 + bar * 0.98); bo.connect(bg).connect(dry); bo.start(t0); bo.stop(t0 + bar);
      // pluck arpeggio: eighth notes over chord tones, with seeded rests so it breathes
      if (b === 0) continue;                                  // let the pad open alone first
      for (let s = 0; s < 8; s++) {
        if (r() < 0.32) continue;
        const ts = t0 + s * beat / 2 + (r() - 0.5) * 0.012;   // tiny human timing
        const tone = chord[(s * 2 + b) % chord.length] + (s >= 4 ? 12 : 0);
        const o = ctx.createOscillator(); o.type = "sine"; o.frequency.value = hz(key + 24 + tone);
        const o2 = ctx.createOscillator(); o2.type = "triangle"; o2.frequency.value = hz(key + 24 + tone) * 2;
        const g = ctx.createGain(); const v = 0.05 + r() * 0.03;
        g.gain.setValueAtTime(0, ts); g.gain.linearRampToValueAtTime(v, ts + 0.008); g.gain.exponentialRampToValueAtTime(0.0001, ts + 1.1);
        const g2 = ctx.createGain(); g2.gain.value = 0.18;
        o.connect(g); o2.connect(g2).connect(g);
        const pan = ctx.createStereoPanner(); pan.pan.value = (r() - 0.5) * 0.7;
        g.connect(pan); pan.connect(dry); pan.connect(delay); pan.connect(verb);
        o.start(ts); o2.start(ts); o.stop(ts + 1.2); o2.stop(ts + 1.2);
      }
    }
    return ctx.startRendering();
  }

  // Encode to Opus/WebM with MediaRecorder (plays the buffer into a recorder in real time).
  async function encode(buffer) {
    const ac = new AudioContext({ sampleRate: SR });
    await ac.resume();
    const src = ac.createBufferSource(); src.buffer = buffer;
    const dest = ac.createMediaStreamDestination(); src.connect(dest);
    const rec = new MediaRecorder(dest.stream, { mimeType: "audio/webm;codecs=opus", audioBitsPerSecond: 160000 });
    const chunks = []; rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    const stopped = new Promise((res) => (rec.onstop = res));
    rec.start(250); src.start();
    await new Promise((res) => (src.onended = res));
    await new Promise((res) => setTimeout(res, 300));
    rec.stop(); await stopped; await ac.close();
    const bytes = new Uint8Array(await new Blob(chunks, { type: "audio/webm" }).arrayBuffer());
    let bin = ""; for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(bin);
  }

  window.music = { render, encode };
})();
