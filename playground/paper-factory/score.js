/*
 * Original score synced to the film (synthesised, copyright-free). window.score.render() -> AudioBuffer;
 * window.score.encode(buf) -> Opus/WebM base64 (plays in real time).
 *   0-9.7 s  playful factory plucks + soft "clunk" on each stamp (3.95, 8.55)
 *   9.75-11  wobble tension, rising    11.0 BOOM    12-17 epic drums + brass chords
 *   17.2-18.6 everything drops out, a deflating "wah-wah" for the shrug   18.6-20 the plucks return
 */
(() => {
  const SR = 48000, D = 20, hz = (m) => 440 * Math.pow(2, (m - 69) / 12);
  async function render() {
    const c = new OfflineAudioContext(2, SR * D, SR), out = c.createDynamicsCompressor(); out.connect(c.destination);
    const ir = c.createBuffer(2, SR * 2.5, SR);
    for (let ch = 0; ch < 2; ch++) { const d = ir.getChannelData(ch); for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / d.length, 3); }
    const verb = c.createConvolver(); verb.buffer = ir; const wet = c.createGain(); wet.gain.value = 0.35; verb.connect(wet).connect(out);
    const bus = c.createGain(); bus.connect(out); bus.connect(verb);
    const tone = (t, m, dur, type, v, glideTo) => { const o = c.createOscillator(), g = c.createGain(); o.type = type; o.frequency.setValueAtTime(hz(m), t);
      if (glideTo != null) o.frequency.linearRampToValueAtTime(hz(glideTo), t + dur);
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + 0.01); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
      o.connect(g).connect(bus); o.start(t); o.stop(t + dur + 0.05); };
    const noise = (t, dur, v, f, type = "lowpass") => { const b = c.createBuffer(1, SR * dur, SR), d = b.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
      const s = c.createBufferSource(), fl = c.createBiquadFilter(), g = c.createGain(); s.buffer = b; fl.type = type; fl.frequency.value = f;
      g.gain.setValueAtTime(v, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur); s.connect(fl).connect(g).connect(bus); s.start(t); };
    const kick = (t, v = 0.9) => { tone(t, 40, 0.35, "sine", v, 26); noise(t, 0.05, v * 0.3, 2000); };
    // playful plucks (C major bounce), 0-9.7 and 18.6-20
    const riff = [60, 64, 67, 72, 67, 64, 65, 69], bass = [48, 48, 53, 55];
    const plucks = (a, b) => { for (let i = 0, t = a; t < b; i++, t += 0.25) { tone(t, riff[i % 8] + 12, 0.25, "triangle", 0.09);
      if (i % 4 === 0) tone(t, bass[(i / 4) % 4], 0.45, "sine", 0.22); if (i % 2 === 1) noise(t, 0.03, 0.05, 6000, "highpass"); } };
    plucks(0.2, 9.7); plucks(18.65, 19.9);
    [3.95, 8.55].forEach((t) => { kick(t, 0.8); noise(t, 0.12, 0.25, 900); tone(t + 0.05, 84, 0.6, "sine", 0.08); tone(t + 0.1, 91, 0.6, "sine", 0.06); });   // stamp + sparkle
    tone(5.6, 72, 2.6, "sine", 0.05, 79);                       // crane lift
    for (let t = 9.75; t < 11; t += 0.11) tone(t, 62 + (t - 9.75) * 8, 0.1, "square", 0.04);   // wobble tension
    noise(9.9, 1.1, 0.04, 3000, "highpass");
    kick(11, 1.2); noise(11, 2.2, 0.7, 500); noise(11, 1.2, 0.3, 4000, "highpass"); tone(11, 36, 2, "sawtooth", 0.2, 24);   // BOOM
    // epic section: taiko-ish drums + brass-like stacked saws, Am F C G
    const prog = [[57, 60, 64], [53, 57, 60], [48, 55, 60], [55, 59, 62]];
    for (let b = 0; b < 4; b++) { const t0 = 12 + b * 1.3;
      prog[b].forEach((m) => [0, 12].forEach((o) => tone(t0, m + o, 1.35, "sawtooth", 0.035)));
      tone(t0, prog[b][0] - 24, 1.3, "sine", 0.3);
      for (const k of [0, 0.325, 0.65, 0.81, 0.975]) kick(t0 + k, k ? 0.6 : 1);
      noise(t0 + 0.65, 0.2, 0.25, 1800, "bandpass"); }
    kick(17.15, 1); noise(17.15, 0.6, 0.3, 3000, "highpass");   // hit, then silence for the shrug
    tone(17.6, 58, 0.35, "sawtooth", 0.07, 57); tone(18.0, 57, 0.55, "sawtooth", 0.07, 54);   // wah-wah
    return c.startRendering();
  }
  async function encode(buf) {
    const ac = new AudioContext({ sampleRate: SR }); await ac.resume(); const s = ac.createBufferSource(); s.buffer = buf;
    const dest = ac.createMediaStreamDestination(); s.connect(dest);
    const rec = new MediaRecorder(dest.stream, { mimeType: "audio/webm;codecs=opus", audioBitsPerSecond: 160000 }), ch = [];
    rec.ondataavailable = (e) => e.data.size && ch.push(e.data); const stop = new Promise((r) => (rec.onstop = r));
    rec.start(250); s.start(); await new Promise((r) => (s.onended = r)); await new Promise((r) => setTimeout(r, 300)); rec.stop(); await stop;
    const u = new Uint8Array(await new Blob(ch).arrayBuffer()); let b = ""; for (let i = 0; i < u.length; i += 0x8000) b += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
    return btoa(b);
  }
  window.score = { render, encode };
})();
