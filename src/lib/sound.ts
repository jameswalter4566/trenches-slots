// Synthesized SFX — Web Audio only, no samples, nothing to license.
class Sfx {
	private ctx: AudioContext | null = null;
	private muted = false;

	setMuted(m: boolean) { this.muted = m; }
	isMuted() { return this.muted; }

	private ensure(): AudioContext | null {
		if (this.muted) return null; // single gate — every sound routes through ensure()
		try {
			if (!this.ctx) this.ctx = new AudioContext();
			if (this.ctx.state === 'suspended') void this.ctx.resume();
			return this.ctx;
		} catch {
			return null;
		}
	}

	private tone(freq: number, dur: number, opts: { type?: OscillatorType; gain?: number; delay?: number; slideTo?: number } = {}) {
		const ctx = this.ensure();
		if (!ctx || ctx.state !== 'running') return;
		const t0 = ctx.currentTime + (opts.delay ?? 0);
		const osc = ctx.createOscillator();
		const g = ctx.createGain();
		osc.type = opts.type ?? 'sine';
		osc.frequency.setValueAtTime(freq, t0);
		if (opts.slideTo) osc.frequency.exponentialRampToValueAtTime(Math.max(20, opts.slideTo), t0 + dur);
		g.gain.setValueAtTime(0, t0);
		g.gain.linearRampToValueAtTime(opts.gain ?? 0.07, t0 + 0.008);
		g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
		osc.connect(g).connect(ctx.destination);
		osc.start(t0);
		osc.stop(t0 + dur + 0.02);
	}

	private noise(dur: number, gain: number, delay = 0, freq = 900) {
		const ctx = this.ensure();
		if (!ctx || ctx.state !== 'running') return;
		const t0 = ctx.currentTime + delay;
		const buf = ctx.createBuffer(1, ctx.sampleRate * dur, ctx.sampleRate);
		const d = buf.getChannelData(0);
		for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length);
		const src = ctx.createBufferSource();
		src.buffer = buf;
		const g = ctx.createGain();
		g.gain.setValueAtTime(gain, t0);
		g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
		const lp = ctx.createBiquadFilter();
		lp.type = 'lowpass';
		lp.frequency.setValueAtTime(freq, t0);
		src.connect(lp).connect(g).connect(ctx.destination);
		src.start(t0);
	}

	unlock() { this.ensure(); }

	spin() { this.noise(0.28, 0.1, 0, 1600); this.tone(300, 0.25, { type: 'triangle', gain: 0.05, slideTo: 90 }); }
	land(i: number) { this.tone(520 + i * 40, 0.045, { type: 'square', gain: 0.03 }); }
	winPulse() { this.tone(660, 0.14, { gain: 0.08 }); this.tone(990, 0.18, { gain: 0.06, delay: 0.07 }); }
	explode() { this.noise(0.22, 0.16, 0, 700); this.tone(220, 0.18, { type: 'sawtooth', gain: 0.05, slideTo: 70 }); }
	orbLand() { this.tone(1245, 0.3, { gain: 0.07 }); this.tone(1865, 0.42, { gain: 0.05, delay: 0.05 }); }
	orbApply() { [880, 1108, 1318, 1760].forEach((f, i) => this.tone(f, 0.16, { gain: 0.08, delay: i * 0.06 })); }
	scatterLand() { this.tone(196, 0.55, { type: 'triangle', gain: 0.12 }); this.tone(392, 0.4, { gain: 0.07, delay: 0.04 }); }
	rollTick() { this.tone(1040, 0.035, { type: 'square', gain: 0.03 }); }
	win() { [523, 659, 784, 1047].forEach((f, i) => this.tone(f, 0.22, { gain: 0.1, delay: i * 0.09 })); }
	bigWin() {
		[392, 523, 659, 784, 1047, 1318].forEach((f, i) => this.tone(f, 0.3, { gain: 0.11, delay: i * 0.1 }));
		this.noise(0.5, 0.06, 0.55, 2400);
	}
	fsTrigger() {
		[262, 330, 392, 523, 659, 784].forEach((f, i) => this.tone(f, 0.35, { type: 'triangle', gain: 0.1, delay: i * 0.11 }));
	}
}

export const sfx = new Sfx();
