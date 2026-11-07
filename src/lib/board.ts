// GOD CANDLE — PixiJS board engine. Pure presentation: it REPLAYS a resolved
// SpinResult (the event book) and never decides money. All symbol art is drawn
// in code or uses system emoji glyphs as prototype placeholders — final art
// swaps in behind buildCellContent() without touching the choreography.

import { AnimatedSprite, Application, Assets, Container, Graphics, Rectangle, Sprite, Text, Texture } from 'pixi.js';
import { COLS, ROWS, SYMBOL_META, COIN_COLORS, type Cell, type SymbolId } from './paytable';
import type { SpinResult, TumbleStep } from './sim';
import { fmtMoney } from './session';
import { sfx } from './sound';

const CELL = 104;
const TILE = 94;
const BOARD_W = COLS * CELL;
const BOARD_H = ROWS * CELL;
const FRAME = 26;
const METER_H = 74;
const LW = BOARD_W + FRAME * 2;
const LH = BOARD_H + FRAME * 2 + METER_H + 14;

const GREEN = 0x2be26a;
const GOLD = 0xf7c843;
const EMOJI_FONT = 'Segoe UI Emoji, Apple Color Emoji, Noto Color Emoji, sans-serif';

// ---------- tweens ----------
type Ease = (x: number) => number;
const outCubic: Ease = (x) => 1 - Math.pow(1 - x, 3);
const inCubic: Ease = (x) => x * x * x;
const outBack: Ease = (x) => 1 + 2.3 * Math.pow(x - 1, 3) + 1.3 * Math.pow(x - 1, 2);
const outBounce: Ease = (x) => {
	const n1 = 7.5625, d1 = 2.75;
	if (x < 1 / d1) return n1 * x * x;
	if (x < 2 / d1) return n1 * (x -= 1.5 / d1) * x + 0.75;
	if (x < 2.5 / d1) return n1 * (x -= 2.25 / d1) * x + 0.9375;
	return n1 * (x -= 2.625 / d1) * x + 0.984375;
};

interface Tween { t: number; dur: number; ease: Ease; apply: (v: number) => void; resolve: () => void }

type CellSprite = Container & { cellData: Cell; idlePhase: number; gleam?: Graphics; sheetIdle?: boolean };

interface SheetAnim { frames: Texture[]; fps: number }

const SYMBOL_IDS: SymbolId[] = [
	'rocket', 'whale', 'frog', 'diamond', 'moon',
	'coinG', 'coinP', 'coinB', 'coinT', 'scatter', 'orb',
];

// Per-symbol idle motion (subtle, phase-offset per cell so the board never moves in lockstep)
const IDLE: Record<SymbolId, { bob?: number; bobMs?: number; rot?: number; rotMs?: number; pulse?: number; pulseMs?: number }> = {
	rocket:  { bob: 3.6, bobMs: 420, rot: 0.03, rotMs: 560 },   // gently hovers
	whale:   { bob: 3.0, bobMs: 820, rot: 0.05, rotMs: 980 },   // floats
	frog:    { bob: 2.2, bobMs: 620, pulse: 0.02, pulseMs: 500 },
	diamond: { pulse: 0.014, pulseMs: 900 },                    // + gleam shimmer
	moon:    { rot: 0.07, rotMs: 1150 },                        // slowly rocks
	coinG:   { bob: 2.6, bobMs: 360 },                          // small bounce
	coinP:   { pulse: 0.03, pulseMs: 540 },                     // pulses
	coinB:   { rot: 0.10, rotMs: 820 },                         // rotates back and forth
	coinT:   { pulse: 0.02, pulseMs: 720 },                     // + twinkle gleam
	scatter: { bob: 2.0, bobMs: 800, pulse: 0.03, pulseMs: 620 },
	orb:     { pulse: 0.025, pulseMs: 320, rot: 0.02, rotMs: 430 },
};

const GLEAM = new Set<SymbolId>(['diamond', 'coinT']);

const PARTICLE: Record<SymbolId, number> = {
	rocket: 0xff9a3d, whale: 0x5aa2ff, frog: 0x3bd45f, diamond: 0xcfeaff,
	moon: 0xf7c843, coinG: 0xf7c843, coinP: 0xb479ff, coinB: 0x5aa2ff,
	coinT: 0x3ee6c2, scatter: 0x2be26a, orb: 0xf7c843,
};

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export class SlotBoard {
	private app!: Application;
	private root = new Container();
	private boardLayer = new Container();
	private fxLayer = new Container();
	private overlayLayer = new Container();
	private sprites: (CellSprite | null)[][] = [];
	private tweens: Tween[] = [];
	private particles: { g: Graphics; vx: number; vy: number; life: number; max: number }[] = [];
	private meterText!: Text;
	private meterPlaque!: Graphics;
	private multBadge!: Text;
	private shake = 0;
	private meterShown = 0;
	private firstSpin = true;
	private textures = new Map<SymbolId, Texture>();
	private anims = new Map<string, SheetAnim>();
	private time = 0;
	private idleOn = false;

	onSettled?: (totalWinMicro: number) => void;

	async init(el: HTMLElement) {
		this.app = new Application();
		await this.app.init({
			background: '#0c0d11',
			antialias: true,
			resolution: Math.min(2, window.devicePixelRatio || 1),
			autoDensity: true,
			width: el.clientWidth,
			height: el.clientHeight,
		});
		el.appendChild(this.app.canvas);
		this.app.stage.addChild(this.root);

		// custom art: any /symbols/<id>.png present is used; otherwise drawn fallback
		await Promise.all(SYMBOL_IDS.map(async (id) => {
			try {
				const tex = await Assets.load<Texture>(`/symbols/${id}.png`);
				this.textures.set(id, tex);
			} catch { /* not generated yet */ }
		}));
		// sprite-sheet animations produced by tools/slice_sheet.py: <id>_win / <id>_idle strips
		await Promise.all(SYMBOL_IDS.flatMap((id) => (['win', 'idle'] as const).map(async (kind) => {
			try {
				const res = await fetch(`/symbols/anim/${id}_${kind}.json`);
				if (!res.ok) return;
				const meta = (await res.json()) as { frames: number; fw: number; fh: number; fps: number };
				const base = await Assets.load<Texture>(`/symbols/anim/${id}_${kind}.png`);
				const frames: Texture[] = [];
				for (let i = 0; i < meta.frames; i++) {
					frames.push(new Texture({ source: base.source, frame: new Rectangle(i * meta.fw, 0, meta.fw, meta.fh) }));
				}
				this.anims.set(`${id}_${kind}`, { frames, fps: meta.fps || 14 });
			} catch { /* no sheet yet */ }
		})));

		this.drawFrame();
		this.boardLayer.x = FRAME;
		this.boardLayer.y = FRAME;
		this.fxLayer.x = FRAME;
		this.fxLayer.y = FRAME;
		this.root.addChild(this.boardLayer, this.fxLayer, this.overlayLayer);
		this.buildMeter();
		this.buildMultBadge();

		for (let c = 0; c < COLS; c++) this.sprites[c] = new Array(ROWS).fill(null);

		const fit = () => {
			const w = el.clientWidth, h = el.clientHeight;
			if (!w || !h) return;
			this.app.renderer.resize(w, h);
			const s = Math.min(w / LW, h / LH);
			this.root.scale.set(s);
			this.root.x = (w - LW * s) / 2;
			this.root.y = (h - LH * s) / 2;
		};
		fit();
		new ResizeObserver(fit).observe(el);

		this.app.ticker.add((tk) => this.update(tk.deltaMS));
	}

	// ---------- static chrome ----------
	private drawFrame() {
		const g = new Graphics();
		// hard offset shadow (brand: chunky 3D, no gradients)
		g.roundRect(8, 10, LW - 8, BOARD_H + FRAME * 2 - 2, 26).fill({ color: 0x000000, alpha: 0.45 });
		g.roundRect(0, 0, LW, BOARD_H + FRAME * 2, 26).fill(0x171a22);
		g.roundRect(0, 0, LW, BOARD_H + FRAME * 2, 26).stroke({ width: 3, color: 0x262b38 });
		g.roundRect(FRAME - 8, FRAME - 8, BOARD_W + 16, BOARD_H + 16, 18).fill(0x0e1016);
		g.roundRect(FRAME - 8, FRAME - 8, BOARD_W + 16, BOARD_H + 16, 18).stroke({ width: 2, color: GREEN, alpha: 0.35 });
		this.root.addChild(g);
	}

	private buildMeter() {
		const y = BOARD_H + FRAME * 2 + 14;
		this.meterPlaque = new Graphics();
		this.redrawMeter(0x171a22, 0x262b38);
		this.meterPlaque.y = y;
		this.meterText = new Text({
			text: '',
			style: { fontFamily: 'DynaPuff', fontSize: 30, fontWeight: '700', fill: 0xffffff },
		});
		this.meterText.anchor.set(0.5);
		this.meterText.x = LW / 2;
		this.meterText.y = y + METER_H / 2;
		this.root.addChild(this.meterPlaque, this.meterText);
		this.setMeterIdle();
	}

	private redrawMeter(fill: number, edge: number) {
		this.meterPlaque.clear();
		this.meterPlaque.roundRect(LW / 2 - 194, 6, 388, METER_H - 6, 18).fill({ color: 0x000000, alpha: 0.4 });
		this.meterPlaque.roundRect(LW / 2 - 200, 0, 400, METER_H - 6, 18).fill(fill);
		this.meterPlaque.roundRect(LW / 2 - 200, 0, 400, METER_H - 6, 18).stroke({ width: 3, color: edge });
	}

	private setMeterIdle() {
		this.meterText.text = 'PUMP IT';
		this.meterText.style.fill = 0x7a8294;
		this.redrawMeter(0x171a22, 0x262b38);
	}

	private setMeterWin(micro: number) {
		this.meterShown = micro;
		this.meterText.text = `WIN  ${fmtMoney(micro)}`;
		this.meterText.style.fill = 0xffffff;
		this.redrawMeter(0x123b23, GREEN);
	}

	private buildMultBadge() {
		this.multBadge = new Text({
			text: '',
			style: {
				fontFamily: 'DynaPuff', fontSize: 34, fontWeight: '700', fill: GOLD,
				stroke: { color: 0x3a2a00, width: 5 },
			},
		});
		this.multBadge.anchor.set(1, 0);
		this.multBadge.x = LW - 14;
		this.multBadge.y = 10;
		this.multBadge.visible = false;
		this.root.addChild(this.multBadge);
	}

	/** Free-spins running total multiplier badge (null hides it). */
	setMultBadge(total: number | null) {
		if (total == null || total <= 0) { this.multBadge.visible = false; return; }
		this.multBadge.text = `x${total}`;
		this.multBadge.visible = true;
	}

	// ---------- symbol art ----------
	private sheetSprite(anim: SheetAnim, fit: number): AnimatedSprite {
		const a = new AnimatedSprite(anim.frames);
		a.anchor.set(0.5);
		a.animationSpeed = anim.fps / 60;
		a.loop = true;
		a.scale.set(fit / Math.max(a.texture.width, a.texture.height));
		a.play();
		return a;
	}

	private buildCellSprite(cell: Cell): CellSprite {
		const c = new Container() as CellSprite;
		c.cellData = cell;
		c.idlePhase = Math.random() * Math.PI * 2;
		const meta = SYMBOL_META[cell.sym];
		const tex = this.textures.get(cell.sym);
		const idleSheet = this.anims.get(`${cell.sym}_idle`);

		if (cell.sym === 'orb') {
			if (idleSheet) {
				c.addChild(this.sheetSprite(idleSheet, 96), this.orbLabel(cell.orb ?? 2));
				c.sheetIdle = true;
			} else {
				c.addChild(tex ? this.buildTexOrb(tex, cell.orb ?? 2) : this.buildOrb(cell.orb ?? 2));
			}
			return c;
		}
		if (cell.sym === 'scatter') {
			if (idleSheet) {
				const glow = new Graphics();
				glow.circle(0, 0, 48).fill({ color: GREEN, alpha: 0.12 });
				c.addChild(glow, this.sheetSprite(idleSheet, 100));
				c.sheetIdle = true;
			} else {
				c.addChild(tex ? this.buildTexScatter(tex) : this.buildScatter());
			}
			return c;
		}
		if (idleSheet) {
			c.addChild(this.sheetSprite(idleSheet, 92));
			c.sheetIdle = true;
			this.addGleam(c);
			return c;
		}
		if (tex) {
			// custom art floats free on the board, Gates-style — no tile behind it
			const sp = new Sprite(tex);
			sp.anchor.set(0.5);
			sp.scale.set(92 / Math.max(sp.texture.width, sp.texture.height));
			c.addChild(sp);
			this.addGleam(c);
			return c;
		}

		const tile = new Graphics();
		const t2 = TILE / 2;
		tile.roundRect(-t2, -t2 + 5, TILE, TILE, 20).fill(meta.edge);       // hard bottom edge = chunky 3D
		tile.roundRect(-t2, -t2, TILE, TILE - 5, 20).fill(meta.tile);
		tile.roundRect(-t2, -t2, TILE, TILE - 5, 20).stroke({ width: 2, color: 0xffffff, alpha: 0.08 });
		c.addChild(tile);

		if (cell.sym in COIN_COLORS) {
			const col = COIN_COLORS[cell.sym];
			const coin = new Graphics();
			coin.circle(0, 2, 33).fill(col.rim);
			coin.circle(0, -2, 31).fill(col.face);
			coin.circle(0, -2, 23).stroke({ width: 3, color: col.rim, alpha: 0.7 });
			c.addChild(coin);
			const glyph = new Text({
				text: meta.glyph,
				style: { fontFamily: 'DynaPuff', fontSize: 30, fontWeight: '700', fill: col.glyph },
			});
			glyph.anchor.set(0.5);
			glyph.y = -2;
			c.addChild(glyph);
		} else {
			const glyph = new Text({ text: meta.glyph, style: { fontFamily: EMOJI_FONT, fontSize: 54 } });
			glyph.anchor.set(0.5);
			glyph.y = -2;
			c.addChild(glyph);
		}
		this.addGleam(c);
		return c;
	}

	private addGleam(c: CellSprite) {
		if (!GLEAM.has(c.cellData.sym)) return;
		const g = new Graphics();
		g.star(0, 0, 4, 10, 3.5).fill(0xffffff);
		g.x = -15;
		g.y = -17;
		g.alpha = 0;
		c.addChild(g);
		c.gleam = g;
	}

	private orbLabel(value: number): Text {
		const label = new Text({
			text: `x${value}`,
			style: {
				fontFamily: 'DynaPuff', fontSize: 28, fontWeight: '700', fill: 0xffffff,
				stroke: { color: 0x6b4e00, width: 6 },
			},
		});
		label.anchor.set(0.5);
		label.y = 32;
		return label;
	}

	private buildTexOrb(tex: Texture, value: number): Container {
		const c = new Container();
		const sp = new Sprite(tex);
		sp.anchor.set(0.5);
		sp.scale.set(96 / Math.max(sp.texture.width, sp.texture.height));
		c.addChild(sp, this.orbLabel(value));
		return c;
	}

	private buildTexScatter(tex: Texture): Container {
		const c = new Container();
		const glow = new Graphics();
		glow.circle(0, 0, 48).fill({ color: GREEN, alpha: 0.12 });
		c.addChild(glow);
		const sp = new Sprite(tex);
		sp.anchor.set(0.5);
		sp.scale.set(100 / Math.max(sp.texture.width, sp.texture.height));
		c.addChild(sp);
		return c;
	}

	private buildOrb(value: number): Container {
		const c = new Container();
		const g = new Graphics();
		g.circle(0, 0, 46).fill({ color: GOLD, alpha: 0.14 });
		g.circle(0, 0, 38).fill({ color: GOLD, alpha: 0.2 });
		g.circle(0, 2, 33).fill(0xb8860b);
		g.circle(0, -1, 31).fill(GOLD);
		g.circle(-10, -12, 9).fill({ color: 0xffffff, alpha: 0.5 });
		// god-candle mark inside the orb
		g.rect(-2, -16, 4, 10).fill(0x0f7a38);
		g.rect(-7, -6, 14, 22).fill(0x11a047);
		g.rect(-2, 16, 4, 6).fill(0x0f7a38);
		c.addChild(g);
		const label = new Text({
			text: `x${value}`,
			style: {
				fontFamily: 'DynaPuff', fontSize: 26, fontWeight: '700', fill: 0xffffff,
				stroke: { color: 0x6b4e00, width: 5 },
			},
		});
		label.anchor.set(0.5);
		label.y = 30;
		c.addChild(label);
		return c;
	}

	private buildScatter(): Container {
		const c = new Container();
		const g = new Graphics();
		g.circle(0, 0, 47).fill({ color: GREEN, alpha: 0.1 });
		g.circle(0, 0, 40).fill({ color: GREEN, alpha: 0.12 });
		// the GOD CANDLE: thick green candle, wick both ends, golden base ring
		g.rect(-3, -42, 6, 12).fill(0x1b9c4d);
		g.roundRect(-13, -30, 26, 56, 6).fill(GREEN);
		g.roundRect(-13, -30, 26, 56, 6).stroke({ width: 3, color: 0x0f7a38 });
		g.rect(-3, 26, 6, 10).fill(0x1b9c4d);
		g.ellipse(0, 38, 20, 7).fill(GOLD);
		g.ellipse(0, 38, 20, 7).stroke({ width: 2, color: 0xb8860b });
		c.addChild(g);
		const label = new Text({
			text: 'SCATTER',
			style: {
				fontFamily: 'DynaPuff', fontSize: 15, fontWeight: '700', fill: GOLD,
				stroke: { color: 0x3a2a00, width: 4 },
			},
		});
		label.anchor.set(0.5);
		label.y = 44;
		c.addChild(label);
		return c;
	}

	// ---------- tween/particle core ----------
	private tween(dur: number, ease: Ease, apply: (v: number) => void): Promise<void> {
		return new Promise((resolve) => {
			this.tweens.push({ t: 0, dur, ease, apply, resolve });
		});
	}

	private update(dt: number) {
		this.time += dt;
		if (this.idleOn) {
			// per-symbol idle motion, phase-offset per cell — alive, never lockstep
			for (let c = 0; c < COLS; c++) {
				for (let r = 0; r < ROWS; r++) {
					const sp = this.sprites[c][r];
					if (!sp) continue;
					if (sp.gleam) sp.gleam.alpha = Math.max(0, Math.sin(this.time / 650 + sp.idlePhase * 2)) ** 6;
					if (sp.sheetIdle) continue; // frames carry the motion
					const idle = IDLE[sp.cellData.sym];
					const p = sp.idlePhase;
					sp.y = this.cy(r) + (idle.bob ? Math.sin(this.time / idle.bobMs! + p) * idle.bob : 0);
					if (idle.rot) sp.rotation = Math.sin(this.time / idle.rotMs! + p) * idle.rot;
					if (idle.pulse) sp.scale.set(1 + Math.sin(this.time / idle.pulseMs! + p) * idle.pulse);
				}
			}
		}
		for (let i = this.tweens.length - 1; i >= 0; i--) {
			const tw = this.tweens[i];
			tw.t += dt;
			const x = Math.min(1, tw.t / tw.dur);
			tw.apply(tw.ease(x));
			if (x >= 1) {
				this.tweens.splice(i, 1);
				tw.resolve();
			}
		}
		for (let i = this.particles.length - 1; i >= 0; i--) {
			const p = this.particles[i];
			p.life += dt;
			p.g.x += (p.vx * dt) / 1000;
			p.g.y += (p.vy * dt) / 1000;
			p.vy += (1800 * dt) / 1000;
			p.g.alpha = 1 - p.life / p.max;
			p.g.rotation += dt / 300;
			if (p.life >= p.max) {
				p.g.destroy();
				this.particles.splice(i, 1);
			}
		}
		if (this.shake > 0) {
			this.shake = Math.max(0, this.shake - dt);
			const a = (this.shake / 320) * 9;
			this.boardLayer.x = FRAME + (Math.random() - 0.5) * a;
			this.boardLayer.y = FRAME + (Math.random() - 0.5) * a;
		} else {
			this.boardLayer.x = FRAME;
			this.boardLayer.y = FRAME;
		}
	}

	private burst(x: number, y: number, color: number, n = 9) {
		for (let i = 0; i < n; i++) {
			const g = new Graphics();
			const size = 5 + Math.random() * 8;
			g.roundRect(-size / 2, -size / 2, size, size, 2).fill(color);
			g.x = x;
			g.y = y;
			const ang = Math.random() * Math.PI * 2;
			const sp = 260 + Math.random() * 420;
			this.fxLayer.addChild(g);
			this.particles.push({ g, vx: Math.cos(ang) * sp, vy: Math.sin(ang) * sp - 260, life: 0, max: 380 + Math.random() * 240 });
		}
	}

	private cx(col: number) { return col * CELL + CELL / 2; }
	private cy(row: number) { return row * CELL + CELL / 2; }

	// ---------- choreography ----------
	async replaySpin(result: SpinResult): Promise<void> {
		this.idleOn = false;
		this.setMeterIdle();
		this.meterShown = 0;

		if (!this.firstSpin) await this.dropOutAll();
		this.firstSpin = false;

		let running = 0;
		for (let s = 0; s < result.steps.length; s++) {
			const step = result.steps[s];
			await this.dropCells(step, s === 0);
			if (!step.wins.length) break;

			running += step.stepWinMicro;
			await this.presentWins(step);
			await this.explodeWins(step);
			this.rollMeterTo(running);
			await this.collapse(step);
		}

		// multiplier orbs settle the sequence
		if (result.appliedMult > 0 && result.baseWinMicro > 0) {
			await this.applyOrbs(result);
		}
		const tumbleTotal = result.totalWinMicro - result.scatterWinMicro;
		if (tumbleTotal > 0) await this.rollupAsync(tumbleTotal, 420);

		if (result.triggersFreeSpins || result.retrigger) {
			await this.celebrateScatters(result);
		}
		if (result.scatterWinMicro > 0) {
			await this.rollupAsync(result.totalWinMicro, 380);
		}

		const betX = result.totalWinMicro / result.betMicro;
		if (betX >= 25) await this.bigWinOverlay(result.totalWinMicro, betX);
		else if (result.totalWinMicro > 0) { sfx.win(); await sleep(260); }

		this.idleOn = true;
		this.onSettled?.(result.totalWinMicro);
	}

	private async dropOutAll() {
		const jobs: Promise<void>[] = [];
		for (let c = 0; c < COLS; c++) {
			for (let r = 0; r < ROWS; r++) {
				const sp = this.sprites[c][r];
				if (!sp) continue;
				this.sprites[c][r] = null;
				const y0 = sp.y;
				jobs.push(
					this.tween(240 + c * 26, inCubic, (v) => { sp.y = y0 + v * (BOARD_H + 260); })
						.then(() => sp.destroy()),
				);
			}
		}
		sfx.spin();
		await Promise.all(jobs);
	}

	private async dropCells(step: TumbleStep, initial: boolean) {
		const jobs: Promise<void>[] = [];
		const landedCols = new Set<number>();
		for (const n of step.newCells) {
			const sp = this.buildCellSprite(n.cell);
			sp.x = this.cx(n.col);
			const targetY = this.cy(n.row);
			const fromY = -CELL * (1.2 + (initial ? (ROWS - n.row) : 0.4));
			sp.y = fromY;
			this.boardLayer.addChild(sp);
			this.sprites[n.col][n.row] = sp;
			const delay = n.col * (initial ? 55 : 30) + (initial ? (ROWS - n.row) * 18 : 0);
			jobs.push(
				sleep(delay).then(() =>
					this.tween(initial ? 430 : 330, outBounce, (v) => { sp.y = fromY + v * (targetY - fromY); }).then(() => {
						if (!landedCols.has(n.col)) {
							landedCols.add(n.col);
							sfx.land(n.col);
						}
						if (n.cell.sym === 'orb') { sfx.orbLand(); this.burst(sp.x, sp.y, GOLD, 6); }
						if (n.cell.sym === 'scatter') { sfx.scatterLand(); this.burst(sp.x, sp.y, GREEN, 6); }
						// landing impact: quick squash-and-stretch
						sp.scale.set(1.1, 0.84);
						return this.tween(130, outCubic, (v) => {
							sp.scale.set(1.1 - 0.1 * v, 0.84 + 0.16 * v);
						});
					}),
				),
			);
		}
		await Promise.all(jobs);
	}

	private async presentWins(step: TumbleStep) {
		sfx.winPulse();
		const jobs: Promise<void>[] = [];
		for (const w of step.wins) {
			let sx = 0, sy = 0;
			for (const [c, r] of w.cells) {
				sx += this.cx(c); sy += this.cy(r);
				const sp = this.sprites[c][r];
				if (!sp) continue;
				jobs.push(this.tween(480, (x) => Math.sin(x * Math.PI * 2) * 0.5 + 0.5, (v) => {
					sp.scale.set(1 + v * 0.14);
				}).then(() => sp.scale.set(1)));
				// expanding win ring
				const ring = new Graphics();
				ring.circle(0, 0, 38).stroke({ width: 5, color: GREEN, alpha: 0.95 });
				ring.x = this.cx(c);
				ring.y = this.cy(r);
				this.fxLayer.addChild(ring);
				jobs.push(this.tween(430, outCubic, (v) => {
					ring.scale.set(1 + v * 1.1);
					ring.alpha = 1 - v;
				}).then(() => ring.destroy()));
			}
			// floating amount tag at the cluster centroid
			const tag = new Text({
				text: fmtMoney(w.winMicro),
				style: {
					fontFamily: 'DynaPuff', fontSize: 34, fontWeight: '700', fill: 0xffffff,
					stroke: { color: 0x0f7a38, width: 6 },
				},
			});
			tag.anchor.set(0.5);
			tag.x = sx / w.cells.length;
			tag.y = sy / w.cells.length;
			this.fxLayer.addChild(tag);
			jobs.push(this.tween(620, outCubic, (v) => {
				tag.y = sy / w.cells.length - v * 46;
				tag.alpha = v < 0.7 ? 1 : 1 - (v - 0.7) / 0.3;
				tag.scale.set(0.6 + v * 0.5);
			}).then(() => tag.destroy()));
		}
		await Promise.all(jobs);
	}

	private async explodeWins(step: TumbleStep) {
		sfx.explode();
		this.shake = 220;
		const jobs: Promise<void>[] = [];
		for (const w of step.wins) {
			for (const [c, r] of w.cells) {
				const sp = this.sprites[c][r];
				if (!sp) continue;
				this.sprites[c][r] = null;
				jobs.push(this.winExit(sp, w.sym));
			}
		}
		await Promise.all(jobs);
	}

	/** Per-symbol win celebration — each symbol leaves the board its own way. */
	private async winExit(sp: CellSprite, sym: SymbolId): Promise<void> {
		const color = PARTICLE[sym] ?? 0xffffff;
		const x = sp.x, y0 = sp.y;

		// premium path: play the symbol's win sprite sheet when one exists
		const winSheet = this.anims.get(`${sym}_win`);
		if (winSheet) {
			const a = new AnimatedSprite(winSheet.frames);
			a.anchor.set(0.5);
			a.x = x;
			a.y = y0;
			a.animationSpeed = winSheet.fps / 60;
			a.loop = false;
			a.scale.set(128 / Math.max(a.texture.width, a.texture.height));
			this.fxLayer.addChild(a);
			sp.destroy();
			this.burst(x, y0, color, 7);
			await new Promise<void>((resolve) => {
				a.onComplete = () => resolve();
				a.play();
			});
			await this.tween(120, inCubic, (v) => { a.alpha = 1 - v; });
			a.destroy();
			return;
		}
		switch (sym) {
			case 'rocket': {
				// flames ignite, rocket launches off the top of the board
				this.burst(x, y0 + 30, 0xff9a3d, 8);
				await this.tween(300, inCubic, (v) => {
					sp.y = y0 - v * (y0 + 170);
					sp.rotation = -0.08 * v;
					if (v > 0.25 && Math.random() < 0.4) this.burst(sp.x, sp.y + 34, 0xff9a3d, 1);
				});
				sp.destroy();
				return;
			}
			case 'whale': {
				// jumps and splashes
				await this.tween(330, (t) => t, (v) => {
					sp.y = y0 - Math.sin(v * Math.PI) * 48;
					sp.rotation = Math.sin(v * Math.PI * 2) * 0.2;
				});
				this.burst(x, y0 + 16, 0x5aa2ff, 12);
				break;
			}
			case 'frog': {
				// squash, spring and pop
				await this.tween(200, outCubic, (v) => {
					sp.scale.set(1 + 0.3 * v, 1 - 0.35 * v);
				});
				await this.tween(160, outBack, (v) => {
					sp.scale.set(1.3 - 0.3 * v, 0.65 + 0.55 * v);
					sp.y = y0 - v * 26;
				});
				this.burst(x, y0, color, 10);
				break;
			}
			case 'coinG': case 'coinP': case 'coinB': case 'coinT': {
				// coin flip (x-scale cosine) then burst in its own color
				await this.tween(300, (t) => t, (v) => {
					sp.scale.x = Math.abs(Math.cos(v * Math.PI * 3)) * (1 - v * 0.2) + 0.01;
				});
				this.burst(x, y0, color, 9);
				break;
			}
			case 'moon': {
				// spins with golden particles
				this.burst(x, y0, 0xf7c843, 7);
				await this.tween(320, outCubic, (v) => {
					sp.rotation = v * Math.PI * 3;
				});
				break;
			}
			case 'diamond': {
				// bright flash and fragments
				const flash = new Graphics();
				flash.circle(0, 0, 44).fill({ color: 0xffffff, alpha: 0.9 });
				flash.x = x; flash.y = y0;
				this.fxLayer.addChild(flash);
				void this.tween(240, outCubic, (v) => { flash.alpha = 0.9 * (1 - v); flash.scale.set(1 + v * 0.8); })
					.then(() => flash.destroy());
				this.burst(x, y0, 0xcfeaff, 12);
				await sleep(180);
				break;
			}
			default: {
				this.burst(x, y0, color, 8);
				this.burst(x, y0, GREEN, 4);
			}
		}
		await this.tween(150, inCubic, (v) => { sp.scale.set(Math.max(0.01, 1 - v)); sp.alpha = 1 - v; });
		sp.destroy();
	}

	private async collapse(step: TumbleStep) {
		// same deterministic rule as the sim: survivors pack to the bottom
		const jobs: Promise<void>[] = [];
		for (let c = 0; c < COLS; c++) {
			const kept: CellSprite[] = [];
			for (let r = 0; r < ROWS; r++) if (this.sprites[c][r]) kept.push(this.sprites[c][r]!);
			const start = ROWS - kept.length;
			for (let i = 0; i < kept.length; i++) {
				const sp = kept[i];
				const toRow = start + i;
				this.sprites[c][toRow] = sp;
				if (toRow !== Math.round((sp.y - CELL / 2) / CELL)) {
					const y0 = sp.y, y1 = this.cy(toRow);
					if (y0 !== y1) jobs.push(this.tween(210, inCubic, (v) => { sp.y = y0 + v * (y1 - y0); }));
				}
			}
			for (let r = 0; r < start; r++) this.sprites[c][r] = null;
		}
		await Promise.all(jobs);
	}

	private async applyOrbs(result: SpinResult) {
		await sleep(180);
		const targets: { sp: CellSprite; value: number }[] = [];
		for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
			const sp = this.sprites[c][r];
			if (sp?.cellData.sym === 'orb') targets.push({ sp, value: sp.cellData.orb ?? 0 });
		}
		sfx.orbApply();
		const meterX = LW / 2 - FRAME;
		const meterY = BOARD_H + METER_H / 2 + 16;
		const jobs = targets.map(({ sp }, i) =>
			sleep(i * 120).then(() => {
				const x0 = sp.x, y0 = sp.y;
				const mx = (x0 + meterX) / 2 + (Math.random() - 0.5) * 160;
				return this.tween(520, outCubic, (v) => {
					// quadratic bezier toward the win meter
					const u = 1 - v;
					sp.x = u * u * x0 + 2 * u * v * mx + v * v * meterX;
					sp.y = u * u * y0 + 2 * u * v * (y0 - 120) + v * v * meterY;
					sp.scale.set(1 - v * 0.45);
				}).then(() => {
					this.burst(meterX, meterY, GOLD, 7);
					this.shake = 150;
				});
			}),
		);
		await Promise.all(jobs);

		// big multiplier stamp
		const stamp = new Text({
			text: `x${result.appliedMult}`,
			style: {
				fontFamily: 'DynaPuff', fontSize: 92, fontWeight: '700', fill: GOLD,
				stroke: { color: 0x3a2a00, width: 10 },
			},
		});
		stamp.anchor.set(0.5);
		stamp.x = BOARD_W / 2;
		stamp.y = BOARD_H / 2;
		this.fxLayer.addChild(stamp);
		await this.tween(540, outBack, (v) => { stamp.scale.set(v); });
		await sleep(420);
		await this.tween(220, inCubic, (v) => { stamp.alpha = 1 - v; });
		stamp.destroy();
	}

	private async celebrateScatters(result: SpinResult) {
		sfx.fsTrigger();
		const jobs: Promise<void>[] = [];
		for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
			const sp = this.sprites[c][r];
			if (sp?.cellData.sym !== 'scatter') continue;
			this.burst(sp.x, sp.y, GREEN, 10);
			jobs.push(this.tween(700, (x) => Math.sin(x * Math.PI * 3) * 0.5 + 0.5, (v) => {
				sp.scale.set(1 + v * 0.22);
				sp.rotation = (v - 0.5) * 0.16;
			}).then(() => { sp.scale.set(1); sp.rotation = 0; }));
		}
		this.shake = 300;
		await Promise.all(jobs);
	}

	// ---------- win meter ----------
	private rollMeterTo(micro: number) {
		void this.rollupAsync(micro, 300);
	}

	private async rollupAsync(micro: number, dur: number) {
		const from = this.meterShown;
		if (micro === from) { this.setMeterWin(micro); return; }
		let lastTick = 0;
		await this.tween(dur, outCubic, (v) => {
			const val = Math.round(from + (micro - from) * v);
			this.setMeterWin(val);
			if (performance.now() - lastTick > 70) { sfx.rollTick(); lastTick = performance.now(); }
		});
		this.setMeterWin(micro);
	}

	// ---------- big win ----------
	private async bigWinOverlay(totalMicro: number, betX: number) {
		sfx.bigWin();
		const veil = new Graphics();
		veil.rect(0, 0, LW, LH).fill({ color: 0x000000, alpha: 0.72 });
		veil.alpha = 0;
		this.overlayLayer.addChild(veil);

		const title = betX >= 500 ? 'GOD CANDLE!' : betX >= 100 ? 'MEGA PUMP!' : 'BIG WIN!';
		const titleText = new Text({
			text: title,
			style: {
				fontFamily: 'DynaPuff', fontSize: 92, fontWeight: '700', fill: GREEN,
				stroke: { color: 0x083d1c, width: 12 },
			},
		});
		titleText.anchor.set(0.5);
		titleText.x = LW / 2;
		titleText.y = LH / 2 - 60;
		titleText.scale.set(0);
		const amount = new Text({
			text: fmtMoney(totalMicro),
			style: {
				fontFamily: 'DynaPuff', fontSize: 64, fontWeight: '700', fill: GOLD,
				stroke: { color: 0x3a2a00, width: 9 },
			},
		});
		amount.anchor.set(0.5);
		amount.x = LW / 2;
		amount.y = LH / 2 + 46;
		amount.alpha = 0;
		this.overlayLayer.addChild(titleText, amount);

		this.shake = 320;
		await this.tween(200, outCubic, (v) => { veil.alpha = v; });
		await this.tween(520, outBack, (v) => { titleText.scale.set(v); });
		// coin rain
		for (let i = 0; i < 26; i++) {
			setTimeout(() => this.burst(Math.random() * LW, LH * 0.25, i % 2 ? GOLD : GREEN, 4), i * 55);
		}
		let lastTick = 0;
		await this.tween(900, outCubic, (v) => {
			amount.alpha = Math.min(1, v * 2);
			amount.text = fmtMoney(Math.round(totalMicro * v));
			if (performance.now() - lastTick > 60) { sfx.rollTick(); lastTick = performance.now(); }
		});
		amount.text = fmtMoney(totalMicro);
		await sleep(1200);
		await this.tween(260, inCubic, (v) => {
			veil.alpha = 1 - v; titleText.alpha = 1 - v; amount.alpha = 1 - v;
		});
		veil.destroy(); titleText.destroy(); amount.destroy();
	}

	destroy() {
		this.app?.destroy(true);
	}
}
