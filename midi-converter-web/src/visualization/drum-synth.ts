import type { MidiNote } from '../types/midi.types';
import type { DrumMapping } from '../types/mapping.types';

export class DrumSynth {
  private ctx: AudioContext;
  private activeNodes: (OscillatorNode | AudioBufferSourceNode)[] = [];

  constructor(ctx: AudioContext) {
    this.ctx = ctx;
  }

  /** Schedule all notes from songOffset onward. Call once on play. */
  scheduleAll(
    notes: MidiNote[],
    noteMap: Map<number, DrumMapping[]>,
    songOffset: number
  ): void {
    const now = this.ctx.currentTime;
    for (const note of notes) {
      if (note.time < songOffset - 0.001) continue;
      const when = now + (note.time - songOffset);
      if (when < now - 0.01) continue;

      const mappedDrums = noteMap.get(note.note);
      if (!mappedDrums || mappedDrums.length === 0) continue;

      this.triggerAt(mappedDrums[0].drum, when, note.velocity / 127);
    }
  }

  stopAll(): void {
    for (const node of this.activeNodes) {
      try { node.stop(); } catch { /* already stopped */ }
    }
    this.activeNodes = [];
  }

  private triggerAt(drumClass: string, when: number, velocity: number): void {
    if (drumClass.includes('Kick'))   { this.triggerKick(when, velocity); return; }
    if (drumClass.includes('Snare'))  { this.triggerSnare(when, velocity); return; }
    if (drumClass.includes('HiHat')) { this.triggerHiHat(when, velocity); return; }
    if (drumClass.includes('Tom') || drumClass.includes('Bongo') || drumClass.includes('Timp')) {
      this.triggerTom(when, velocity); return;
    }
    if (drumClass.includes('Crash') || drumClass.includes('China') || drumClass.includes('Gong')) {
      this.triggerCymbal(when, velocity, 0.5); return;
    }
    if (drumClass.includes('Ride')) { this.triggerCymbal(when, velocity, 0.9); return; }
    this.triggerDefault(when, velocity);
  }

  private triggerKick(when: number, v: number): void {
    const ctx = this.ctx;

    // Body: sine sweep 150 → 40 Hz
    const bodyGain = ctx.createGain();
    bodyGain.gain.setValueAtTime(v, when);
    bodyGain.gain.exponentialRampToValueAtTime(0.001, when + 0.4);
    bodyGain.connect(ctx.destination);
    const osc = ctx.createOscillator();
    osc.frequency.setValueAtTime(150, when);
    osc.frequency.exponentialRampToValueAtTime(40, when + 0.15);
    osc.connect(bodyGain);
    osc.start(when);
    osc.stop(when + 0.4);
    this.activeNodes.push(osc);

    // Click transient
    const clickGain = ctx.createGain();
    clickGain.gain.setValueAtTime(v * 0.5, when);
    clickGain.gain.exponentialRampToValueAtTime(0.001, when + 0.02);
    clickGain.connect(ctx.destination);
    const click = ctx.createOscillator();
    click.type = 'square';
    click.frequency.value = 200;
    click.connect(clickGain);
    click.start(when);
    click.stop(when + 0.02);
    this.activeNodes.push(click);
  }

  private triggerSnare(when: number, v: number): void {
    const ctx = this.ctx;

    // Noise burst
    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(v * 0.8, when);
    noiseGain.gain.exponentialRampToValueAtTime(0.001, when + 0.2);
    const hpf = ctx.createBiquadFilter();
    hpf.type = 'highpass';
    hpf.frequency.value = 1500;
    hpf.connect(noiseGain);
    noiseGain.connect(ctx.destination);
    const noise = ctx.createBufferSource();
    noise.buffer = this.makeNoiseBuffer(0.2);
    noise.connect(hpf);
    noise.start(when);
    noise.stop(when + 0.2);
    this.activeNodes.push(noise);

    // Body sine
    const bodyGain = ctx.createGain();
    bodyGain.gain.setValueAtTime(v * 0.5, when);
    bodyGain.gain.exponentialRampToValueAtTime(0.001, when + 0.1);
    bodyGain.connect(ctx.destination);
    const osc = ctx.createOscillator();
    osc.frequency.value = 180;
    osc.connect(bodyGain);
    osc.start(when);
    osc.stop(when + 0.1);
    this.activeNodes.push(osc);
  }

  private triggerHiHat(when: number, v: number): void {
    const ctx = this.ctx;
    const decay = 0.06;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(v * 0.4, when);
    gain.gain.exponentialRampToValueAtTime(0.001, when + decay);
    const hpf = ctx.createBiquadFilter();
    hpf.type = 'highpass';
    hpf.frequency.value = 7000;
    hpf.connect(gain);
    gain.connect(ctx.destination);
    const noise = ctx.createBufferSource();
    noise.buffer = this.makeNoiseBuffer(decay);
    noise.connect(hpf);
    noise.start(when);
    noise.stop(when + decay);
    this.activeNodes.push(noise);
  }

  private triggerTom(when: number, v: number): void {
    const ctx = this.ctx;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(v * 0.8, when);
    gain.gain.exponentialRampToValueAtTime(0.001, when + 0.25);
    gain.connect(ctx.destination);
    const osc = ctx.createOscillator();
    osc.frequency.setValueAtTime(110, when);
    osc.frequency.exponentialRampToValueAtTime(55, when + 0.15);
    osc.connect(gain);
    osc.start(when);
    osc.stop(when + 0.25);
    this.activeNodes.push(osc);
  }

  private triggerCymbal(when: number, v: number, decay: number): void {
    const ctx = this.ctx;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(v * 0.35, when);
    gain.gain.exponentialRampToValueAtTime(0.001, when + decay);
    const bpf = ctx.createBiquadFilter();
    bpf.type = 'bandpass';
    bpf.frequency.value = 4000;
    bpf.Q.value = 0.5;
    bpf.connect(gain);
    gain.connect(ctx.destination);
    const noise = ctx.createBufferSource();
    noise.buffer = this.makeNoiseBuffer(decay);
    noise.connect(bpf);
    noise.start(when);
    noise.stop(when + decay);
    this.activeNodes.push(noise);
  }

  private triggerDefault(when: number, v: number): void {
    const ctx = this.ctx;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(v * 0.4, when);
    gain.gain.exponentialRampToValueAtTime(0.001, when + 0.12);
    gain.connect(ctx.destination);
    const osc = ctx.createOscillator();
    osc.frequency.value = 200;
    osc.connect(gain);
    osc.start(when);
    osc.stop(when + 0.12);
    this.activeNodes.push(osc);
  }

  private makeNoiseBuffer(duration: number): AudioBuffer {
    const sampleRate = this.ctx.sampleRate;
    const length = Math.ceil(sampleRate * duration);
    const buffer = this.ctx.createBuffer(1, length, sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < length; i++) data[i] = Math.random() * 2 - 1;
    return buffer;
  }
}
