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
const RED = 0xf0414d;
const GOLD = 0xf7c843;
const CYAN = 0x27d7f5;
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

interface LiveCandle { g: Graphics; label: Text; mult: number; masked: boolean; phase: number; osc: number; revealing?: boolean }
type CellSprite = Container & { cellData: Cell; idlePhase: number; gleam?: Graphics; sheetIdle?: boolean; mc?: LiveCandle };

/** Format a mystery multiplier for the tile label (0.15× / 1× / 25×). */
function fmtMult(v: number): string {
	if (v < 0) return '?';
	return Number.isInteger(v) ? `${v}×` : `${v}×`;
}

interface SheetAnim { frames: Texture[]; fps: number; anchorX: number; anchorY: number; bodyFrac?: number }

const SYMBOL_IDS: SymbolId[] = [
	'goldbar', 'bull', 'bear', 'moneygun', 'vault', 'rocket', 'whale', 'frog', 'diamond', 'moon',
	'terminal', 'coinG', 'coinP', 'coinB', 'coinT', 'scatter', 'orb',
];

// Per-symbol idle motion (subtle, phase-offset per cell so the board never moves in lockstep)
const IDLE: Record<SymbolId, { bob?: number; bobMs?: number; rot?: number; rotMs?: number; pulse?: number; pulseMs?: number }> = {
	goldbar: { bob: 1.4, bobMs: 760, pulse: 0.012, pulseMs: 1100 }, // fallback if no idle sheet
	bull:    { bob: 2.0, bobMs: 700, pulse: 0.015, pulseMs: 900 }, // fallback if no idle sheet
	bear:    { bob: 1.6, bobMs: 820, pulse: 0.015, pulseMs: 1000 }, // fallback if no idle sheet
	moneygun:{ bob: 3.0, bobMs: 500, rot: 0.04, rotMs: 640 },    // fallback if no idle sheet
	vault:   { bob: 1.2, bobMs: 900, pulse: 0.012, pulseMs: 1200 }, // fallback if no idle sheet
	terminal:{ bob: 1.2, bobMs: 900, pulse: 0.01, pulseMs: 1100 }, // fallback if no idle sheet
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
	goldbar: 0xf7c843, bull: 0xffa24d, bear: 0xf0414d, moneygun: 0x3bd45f, vault: 0xf7c843, terminal: 0x27d7f5,
	rocket: 0xff9a3d, whale: 0x5aa2ff, frog: 0x3bd45f, diamond: 0xcfeaff,
	moon: 0xf7c843, coinG: 0xf7c843, coinP: 0xb479ff, coinB: 0x5aa2ff,
	coinT: 0x3ee6c2, scatter: 0x2be26a, orb: 0xf7c843,
};

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

// ---------- candlestick price-action helpers (ported from the crash game chart) ----------
const smoothStep = (t: number) => t * t * (3 - 2 * t);

/** The intra-candle tick path: open → high/low (jittered order) → close. */
function tickPath(o: number, h: number, l: number, c: number, isRug: boolean, rng: () => number): number[] {
	if (isRug) return [o, o * (0.92 + rng() * 0.06), o * (0.5 + rng() * 0.2), c * (1.2 + rng() * 0.3), c, c];
	const range = Math.max(h - l, 1);
	const jit = (v: number, amt: number) => Math.min(h, Math.max(l, v + (rng() - 0.5) * amt));
	const mid = (a: number, b: number, t: number) => a + (b - a) * t;
	const lowFirst = c >= o ? rng() < 0.72 : rng() < 0.28;
	const pts = [o];
	if (lowFirst) pts.push(jit(mid(o, l, 0.6), range * 0.2), l, jit(mid(l, h, 0.45), range * 0.3), h, jit(mid(h, c, 0.5), range * 0.2));
	else pts.push(jit(mid(o, h, 0.6), range * 0.2), h, jit(mid(h, l, 0.45), range * 0.3), l, jit(mid(l, c, 0.5), range * 0.2));
	pts.push(c);
	return pts;
}

export class SlotBoard {
	private app!: Application;
	private root = new Container();
	private boardLayer = new Container();
	private fxLayer = new Container();
	private overlayLayer = new Container();
	private sprites: (CellSprite | null)[][] = [];
	private tweens: Tween[] = [];
	private particles: { g: Graphics; vx: number; vy: number; life: number; max: number }[] = [];
	private bills: { g: Graphics; vx: number; vy: number; vr: number; sway: number; swayPh: number; life: number }[] = [];
	private meterText!: Text;
	private meterPlaque!: Graphics;
	private multBadge!: Text;
	private shake = 0;
	private meterShown = 0;
	private firstSpin = true;
	private textures = new Map<SymbolId, Texture>();
	private anims = new Map<string, SheetAnim>();
	private fadeMaskTex!: Texture;
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
		this.fadeMaskTex = this.buildFadeMask();

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
				const meta = (await res.json()) as { frames: number; fw: number; fh: number; fps: number; anchorX?: number; anchorY?: number; bodyFrac?: number };
				const base = await Assets.load<Texture>(`/symbols/anim/${id}_${kind}.png`);
				const frames: Texture[] = [];
				for (let i = 0; i < meta.frames; i++) {
					frames.push(new Texture({ source: base.source, frame: new Rectangle(i * meta.fw, 0, meta.fw, meta.fh) }));
				}
				this.anims.set(`${id}_${kind}`, {
					frames, fps: meta.fps || 14,
					anchorX: meta.anchorX ?? 0.5, anchorY: meta.anchorY ?? 0.5, bodyFrac: meta.bodyFrac,
				});
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

	// Soft vertical fade mask: opaque over a symbol's own cell (and below, for a
	// downward flame), fading to transparent ~1 tile ABOVE the cell top. A win
	// animation masked with this plays IN FULL — a launch rises and ghosts out as
	// it leaves its slot, instead of being hard-clipped or solidly covering the
	// tile stacked above it.
	private readonly FADE_TOP = CELL * 1.5;   // px of fade region above the cell top
	private readonly FADE_BELOW = CELL * 1.6; // px of opaque region below the cell top
	private buildFadeMask(): Texture {
		const w = Math.round(CELL * 1.6);
		const h = Math.round(this.FADE_TOP + this.FADE_BELOW);
		const canvas = document.createElement('canvas');
		canvas.width = w;
		canvas.height = h;
		const ctx = canvas.getContext('2d')!;
		const grad = ctx.createLinearGradient(0, 0, 0, h);
		grad.addColorStop(0, 'rgba(255,255,255,0)');
		grad.addColorStop(this.FADE_TOP / h, 'rgba(255,255,255,1)');
		grad.addColorStop(1, 'rgba(255,255,255,1)');
		ctx.fillStyle = grad;
		ctx.fillRect(0, 0, w, h);
		return Texture.from(canvas);
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
			// the god-candle: a LIVE candlestick hiding a MYSTERY multiplier. Some tiles
			// show '?', others show their value; one in a while it's the mystery jackpot.
			const g = new Graphics();
			const mult = cell.mystery ?? 1;
			const masked = !!cell.masked || mult < 0;   // jackpot candles stay masked
			const label = new Text({
				text: masked ? '?' : fmtMult(mult), style: {
					fontFamily: 'DynaPuff', fontSize: masked ? 30 : 22, fontWeight: '700', fill: GOLD,
					stroke: { color: 0x3a2a00, width: 5 },
				},
			});
			label.anchor.set(0.5); label.y = 44;
			c.addChild(g, label);
			c.mc = { g, label, mult, masked, phase: Math.random() * 2600, osc: 0 };
			this.drawLiveCandle(c);
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

	/** Redraw a god-candle tile: a green candlestick grown to the current oscillation
	 * (0 = flat at open, 1 = fully up to its preview multiplier), resting on a gold base. */
	private drawLiveCandle(sp: CellSprite) {
		const st = sp.mc!;
		const g = st.g;
		g.clear();
		const base = 30;                                   // candle foot (local y)
		// masked = medium mysterious candle; revealed = body ∝ the multiplier
		const maxH = st.masked ? 34 : 14 + Math.max(0, Math.log(Math.max(1, st.mult))) * 13;
		const bodyH = Math.max(4, maxH * st.osc);
		const top = base - bodyH;
		// aura
		g.roundRect(-18, top - 8, 36, bodyH + 20, 9).fill({ color: GREEN, alpha: 0.14 });
		// gold base ring
		g.ellipse(0, base + 7, 18, 5).fill(GOLD);
		g.ellipse(0, base + 7, 18, 5).stroke({ width: 2, color: 0xb8860b });
		// wick + body
		g.rect(-2, top - 7, 4, 8).fill(GREEN);
		g.roundRect(-13, top, 26, bodyH, 5).fill(GREEN);
		g.roundRect(-13, top, 26, bodyH, 5).stroke({ width: 2, color: 0x0f7a38 });
		g.roundRect(-8, top + 3, 6, Math.max(4, bodyH - 6), 3).fill({ color: 0xffffff, alpha: 0.2 });
	}

	/** Advance a god-candle tile: slow in-place rise then fall (close climbs toward its
	 * preview, then eases back), a gentle ~2.6s cosine loop. */
	private animLiveCandle(sp: CellSprite, dt: number) {
		const st = sp.mc!;
		if (st.revealing) return;   // the reveal controls osc directly
		st.phase += dt;
		st.osc = 0.5 - 0.5 * Math.cos((st.phase / 2600) * Math.PI * 2);
		this.drawLiveCandle(sp);
	}

	/** Reveal every mystery candle on the board (flip '?' → value, grow it), then
	 * collect the summed candle prize onto the win meter. */
	private async revealCandles(result: SpinResult): Promise<void> {
		const jobs: Promise<void>[] = [];
		for (const info of result.candleReveal) {
			const sp = this.sprites[info.col][info.row];
			if (sp?.cellData.sym !== 'scatter' || !sp.mc) continue;
			jobs.push(this.popCandle(sp, info));
		}
		if (!jobs.length) return;
		sfx.winPulse();
		await Promise.all(jobs);
		if (result.candlePrizeMicro > 0) await this.rollupAsync(result.totalWinMicro, 520);
	}

	private async popCandle(sp: CellSprite, info: { mult: number; masked: boolean }): Promise<void> {
		const st = sp.mc!;
		st.revealing = true;
		const px = sp.x + FRAME, py = sp.y + FRAME;
		if (info.mult < 0) {
			st.label.text = 'JACKPOT'; st.label.style.fontSize = 15; st.label.style.fill = 0xffffff;
			this.burst(px, py, GOLD, 18, this.overlayLayer);
			sfx.win();
		} else {
			st.mult = info.mult; st.masked = false;
			st.label.text = fmtMult(info.mult); st.label.style.fontSize = 22; st.label.style.fill = GOLD;
			this.burst(px, py, GOLD, 8, this.overlayLayer);
		}
		// grow the candle to full with a scale pop
		await this.tween(400, outBack, (v) => {
			st.osc = Math.max(0, Math.min(1, v));
			sp.scale.set(1 + Math.sin(Math.min(1, v) * Math.PI) * 0.22);
			this.drawLiveCandle(sp);
		});
		sp.scale.set(1);
	}

	// ---------- tween/particle core ----------
	private tween(dur: number, ease: Ease, apply: (v: number) => void): Promise<void> {
		return new Promise((resolve) => {
			this.tweens.push({ t: 0, dur, ease, apply, resolve });
		});
	}

	private update(dt: number) {
		this.time += dt;
		// live scatter candlesticks fluctuate continuously (even mid-spin)
		for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
			const sp = this.sprites[c][r];
			if (sp?.mc) this.animLiveCandle(sp, dt);
		}
		if (this.idleOn) {
			// per-symbol idle motion, phase-offset per cell — alive, never lockstep
			for (let c = 0; c < COLS; c++) {
				for (let r = 0; r < ROWS; r++) {
					const sp = this.sprites[c][r];
					if (!sp) continue;
					if (sp.mc) continue; // scatter: its own live-candle animation
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
		// money rain: banknotes flutter down from the top across the whole screen
		for (let i = this.bills.length - 1; i >= 0; i--) {
			const b = this.bills[i];
			b.life += dt;
			b.vy = Math.min(360, b.vy + (260 * dt) / 1000);           // gentle gravity, terminal flutter
			b.g.x += ((b.vx + Math.sin(b.life / 170 + b.swayPh) * b.sway) * dt) / 1000;
			b.g.y += (b.vy * dt) / 1000;
			b.g.rotation += (b.vr * dt) / 1000;
			if (b.g.y > LH + 50) { b.g.destroy(); this.bills.splice(i, 1); }
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

	private burst(x: number, y: number, color: number, n = 9, layer?: Container) {
		for (let i = 0; i < n; i++) {
			const g = new Graphics();
			const size = 5 + Math.random() * 8;
			g.roundRect(-size / 2, -size / 2, size, size, 2).fill(color);
			g.x = x;
			g.y = y;
			const ang = Math.random() * Math.PI * 2;
			const sp = 260 + Math.random() * 420;
			(layer ?? this.fxLayer).addChild(g);
			this.particles.push({ g, vx: Math.cos(ang) * sp, vy: Math.sin(ang) * sp - 260, life: 0, max: 380 + Math.random() * 240 });
		}
	}

	private cx(col: number) { return col * CELL + CELL / 2; }
	private cy(row: number) { return row * CELL + CELL / 2; }

	// ---------- choreography ----------
	/** Fill the board with a resting grid on load — a slot never shows an empty cabinet. */
	async primeIdle(grid: Cell[][]) {
		const newCells: { col: number; row: number; cell: Cell }[] = [];
		for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) newCells.push({ col: c, row: r, cell: grid[c][r] });
		await this.dropCells({ grid, newCells, wins: [], orbs: [], stepWinMicro: 0 }, true);
		this.firstSpin = false;
		this.idleOn = true;
	}

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
		// roll the meter up to the GROSS win (before any bear penalty)
		const grossTumble = result.grossWinMicro - result.scatterWinMicro;
		if (grossTumble > 0) await this.rollupAsync(grossTumble, 420);

		if (result.triggersFreeSpins || result.retrigger) {
			await this.celebrateScatters(result);
		}
		if (result.scatterWinMicro > 0) {
			await this.rollupAsync(result.grossWinMicro, 380);
		}

		// BEAR MARKET: a bear on the board roars and crushes the win to the net amount
		if (result.bearCount > 0 && result.grossWinMicro > 0) {
			await this.bearRoar(result);
		}
		// MONEY GUN: guns fire, cash rains down, screen shakes, prize added to the win
		if (result.moneygunPrizes.length > 0) {
			await this.moneyGunFire(result);
		}
		// BANK VAULT: vaults unlock, gold showers, prize added to the win
		if (result.vaultPrizes.length > 0) {
			await this.vaultUnlock(result);
		}
		// MYSTERY CANDLES: reveal each hidden multiplier and collect the prize
		if (result.candleReveal.length > 0) {
			await this.revealCandles(result);
		}

		const betX = result.totalWinMicro / result.betMicro;
		if (betX >= 25) await this.bigWinOverlay(result.totalWinMicro, betX);
		else if (result.totalWinMicro > 0) { sfx.win(); await sleep(260); }

		this.idleOn = true;
		this.onSettled?.(result.totalWinMicro);
	}

	/** BEAR MARKET: every bear on the board rears up and roars (red shockwave),
	 * then the win meter is crushed from the gross win down to the bear-reduced net. */
	private async bearRoar(result: SpinResult): Promise<void> {
		const ov = this.overlayLayer;
		const roar = this.anims.get('bear_win');
		sfx.rug();
		this.shake = 420;

		const veil = new Graphics();
		veil.rect(0, 0, LW, LH).fill({ color: RED, alpha: 1 });
		veil.alpha = 0;
		ov.addChild(veil);

		const banner = new Text({
			text: 'BEAR MARKET', style: {
				fontFamily: 'DynaPuff', fontSize: 40, fontWeight: '700', fill: RED,
				stroke: { color: 0x2a0708, width: 9 },
			},
		});
		banner.anchor.set(0.5); banner.x = LW / 2; banner.y = FRAME + 40; banner.scale.set(0);
		ov.addChild(banner);

		// roar every bear on the board
		const jobs: Promise<void>[] = [];
		for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
			const sp = this.sprites[c][r];
			if (sp?.cellData.sym !== 'bear') continue;
			this.burst(sp.x + FRAME, sp.y + FRAME, RED, 10, ov);
			if (roar) jobs.push(this.playSheetAt(sp, roar));
		}
		await this.tween(220, outCubic, (v) => { veil.alpha = v * 0.34; });
		await this.tween(360, outBack, (v) => banner.scale.set(v));
		await Promise.all(jobs);

		// crush the win: meter rolls DOWN from gross to the bear-reduced pay win
		// (the money-gun prize is sprayed separately, afterwards, and bears can't touch it)
		const netPay = result.totalWinMicro - result.moneygunWinMicro;
		await this.rollupAsync(netPay, 560);
		await sleep(650);
		await this.tween(300, inCubic, (v) => { veil.alpha = 0.34 * (1 - v); banner.alpha = 1 - v; });
		veil.destroy(); banner.destroy();
	}

	/** Play a one-shot sheet once over a cell (body-pinned, soft-fade like a win).
	 * Used for the bear roar and the money-gun fire. */
	private async playSheetAt(sp: CellSprite, sheet: SheetAnim): Promise<void> {
		const a = new AnimatedSprite(sheet.frames);
		a.anchor.set(sheet.anchorX, sheet.anchorY);
		a.x = sp.x; a.y = sp.y;
		a.animationSpeed = sheet.fps / 60;
		a.loop = false;
		const fw = a.texture.width;
		a.scale.set(sheet.bodyFrac ? 84 / (sheet.bodyFrac * fw) : 84 / Math.max(fw, a.texture.height));
		const m = new Sprite(this.fadeMaskTex);
		m.anchor.set(0.5, 0);
		m.x = sp.x; m.y = sp.y - CELL / 2 - this.FADE_TOP;
		a.mask = m;
		this.fxLayer.addChild(m, a);
		sp.visible = false;
		await new Promise<void>((resolve) => { a.onComplete = () => resolve(); a.play(); });
		a.mask = null; m.destroy(); a.destroy();
		sp.visible = true;
	}

	/** Drop one banknote from the top of the screen (money rain). */
	private spawnBill() {
		const g = new Graphics();
		const w = 20 + Math.random() * 10, h = w * 0.5;
		g.roundRect(-w / 2, -h / 2, w, h, 3).fill(0x1f8f3e);
		g.roundRect(-w / 2, -h / 2, w, h, 3).stroke({ width: 1.5, color: 0x8ff0a8, alpha: 0.8 });
		g.circle(0, 0, h * 0.28).fill({ color: 0xbff7cb, alpha: 0.85 });
		g.x = Math.random() * LW;
		g.y = -30;
		g.rotation = Math.random() * Math.PI;
		this.overlayLayer.addChild(g);
		this.bills.push({
			g, vx: (Math.random() - 0.5) * 60, vy: 40 + Math.random() * 80,
			vr: (Math.random() - 0.5) * 4, sway: 30 + Math.random() * 60,
			swayPh: Math.random() * 6.28, life: 0,
		});
	}

	/** MONEY GUN: each gun fires, cash rains across the whole screen, the screen
	 * shakes, and the sprayed prize is added to the win meter. */
	private async moneyGunFire(result: SpinResult): Promise<void> {
		const ov = this.overlayLayer;
		const fire = this.anims.get('moneygun_win');
		sfx.bigWin();

		const banner = new Text({
			text: 'MONEY GUN', style: {
				fontFamily: 'DynaPuff', fontSize: 40, fontWeight: '700', fill: GREEN,
				stroke: { color: 0x05351b, width: 9 },
			},
		});
		banner.anchor.set(0.5); banner.x = LW / 2; banner.y = FRAME + 40; banner.scale.set(0);
		ov.addChild(banner);

		// fire every money gun on the board (+ a cash burst from its muzzle)
		const jobs: Promise<void>[] = [];
		for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
			const sp = this.sprites[c][r];
			if (sp?.cellData.sym !== 'moneygun') continue;
			this.burst(sp.x + FRAME, sp.y + FRAME, GREEN, 10, ov);
			if (fire) jobs.push(this.playSheetAt(sp, fire));
		}
		await this.tween(320, outBack, (v) => banner.scale.set(v));

		// screen-wide money rain + sustained shake for ~1.4s
		const rainMs = 1500;
		let elapsed = 0, acc = 0;
		await this.tween(rainMs, (t) => t, (v) => {
			elapsed = v * rainMs;
			this.shake = Math.max(this.shake, 120);          // keep it rumbling
			acc += 1;
			if (acc >= 2) { acc = 0; this.spawnBill(); this.spawnBill(); }
		});
		await Promise.all(jobs);
		void elapsed;

		// roll the money prize onto the meter (gun total, before vault/candle)
		const gunTarget = result.totalWinMicro - result.vaultWinMicro - result.candlePrizeMicro;
		await this.rollupAsync(gunTarget, 620);
		await sleep(700);
		await this.tween(280, inCubic, (v) => { banner.alpha = 1 - v; });
		banner.destroy();
	}

	/** BANK VAULT: each vault unlocks (door swings open), a gold shower rains, the
	 * screen shakes, and the big prize is added to the win meter. */
	private async vaultUnlock(result: SpinResult): Promise<void> {
		const ov = this.overlayLayer;
		const unlock = this.anims.get('vault_win');
		sfx.bigWin();
		this.shake = 300;

		const banner = new Text({
			text: 'VAULT UNLOCKED', style: {
				fontFamily: 'DynaPuff', fontSize: 38, fontWeight: '700', fill: GOLD,
				stroke: { color: 0x3a2a00, width: 9 },
			},
		});
		banner.anchor.set(0.5); banner.x = LW / 2; banner.y = FRAME + 40; banner.scale.set(0);
		ov.addChild(banner);

		const jobs: Promise<void>[] = [];
		for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
			const sp = this.sprites[c][r];
			if (sp?.cellData.sym !== 'vault') continue;
			this.burst(sp.x + FRAME, sp.y + FRAME, GOLD, 12, ov);
			if (unlock) jobs.push(this.playSheetAt(sp, unlock));
		}
		await this.tween(320, outBack, (v) => banner.scale.set(v));

		// gold shower: banknotes/coins rain for ~1.3s (reuse the money-rain system, gold)
		await this.tween(1300, (t) => t, (v) => {
			this.shake = Math.max(this.shake, 140);
			if (Math.round(v * 60) % 2 === 0) { this.spawnBill(); this.spawnBill(); }
		});
		await Promise.all(jobs);

		// roll the meter up to include the vault prize (candles collect after)
		await this.rollupAsync(result.totalWinMicro - result.candlePrizeMicro, 760);
		await sleep(750);
		await this.tween(300, inCubic, (v) => { banner.alpha = 1 - v; });
		banner.destroy();
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

		// premium path: play the symbol's full win sprite sheet when one exists.
		// Pin the symbol's RESTING body (anchorX/Y) to the tile centre and scale
		// so the body ~= tile size; the launch/jump/flame then overflows the cell
		// naturally instead of the whole tall frame being shrunk to fit.
		const winSheet = this.anims.get(`${sym}_win`);
		if (winSheet) {
			const a = new AnimatedSprite(winSheet.frames);
			a.anchor.set(winSheet.anchorX, winSheet.anchorY);
			a.x = x;
			a.y = y0;
			a.animationSpeed = winSheet.fps / 60;
			a.loop = false;
			const fw = a.texture.width, fh = a.texture.height;
			const TILE = 84;                            // body ~= one tile, never oversized
			const scale = winSheet.bodyFrac
				? TILE / (winSheet.bodyFrac * fw)       // body ~= one tile
				: TILE / Math.max(fw, fh);              // fallback: fit whole frame
			a.scale.set(scale);
			// soft fade: opaque over this cell, transparent ~1 tile above it, so the
			// FULL launch plays but ghosts out as it leaves the slot — never hard-cut,
			// never solidly covering the tile stacked above.
			const m = new Sprite(this.fadeMaskTex);
			m.anchor.set(0.5, 0);
			m.x = x;
			m.y = y0 - CELL / 2 - this.FADE_TOP;        // fade→opaque boundary sits at the cell top
			a.mask = m;
			this.fxLayer.addChild(m, a);
			sp.destroy();
			this.burst(x, y0, color, 7);
			await new Promise<void>((resolve) => {
				a.onComplete = () => resolve();
				a.play();
			});
			await sleep(90);                            // let the final frame breathe
			await this.tween(120, inCubic, (v) => { a.alpha = 1 - v; });
			a.mask = null;
			m.destroy();
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

	// ---------- GOD CANDLE JACKPOT ----------
	/** The scatter god-candle comes alive: a live candlestick charges (fluctuating
	 * open/close), then BOOMS up through the board, shattering the tiles above it,
	 * while a rugs.fun-style multiplier climbs toward a peak (moon) or rugs.
	 * Returns the jackpot win = round(peakX * bet). Pure presentation. */
	async godCandleJackpot(betMicro: number, peakX: number): Promise<number> {
		this.idleOn = false;
		const ov = this.overlayLayer;
		const centreX = LW / 2;
		const moon = peakX >= 50;

		// darken the board
		const veil = new Graphics();
		veil.rect(0, 0, LW, LH).fill({ color: 0x090b12, alpha: 1 });
		veil.alpha = 0;
		ov.addChild(veil);
		sfx.scatterLand();
		await this.tween(240, outCubic, (v) => { veil.alpha = v * 0.94; });

		const title = new Text({
			text: 'GOD CANDLE', style: {
				fontFamily: 'DynaPuff', fontSize: 44, fontWeight: '700', fill: GREEN,
				stroke: { color: 0x05351b, width: 9 },
			},
		});
		title.anchor.set(0.5);
		title.x = centreX; title.y = FRAME + 30; title.alpha = 0;
		ov.addChild(title);
		await this.tween(300, outBack, (v) => { title.scale.set(0.6 + v * 0.4); title.alpha = v; });

		// BOOM: the god candle smashes up through the board, shattering tiles bottom→top
		sfx.bigWin();
		this.shake = 320;
		for (let r = ROWS - 1; r >= 0; r--) { this.shatterRow(r, ov); await sleep(55); }

		// ---- live scrolling candlestick chart (ported from the crash game) ----
		const gridG = new Graphics(), candleG = new Graphics(), pulseG = new Graphics();
		ov.addChild(gridG, candleG, pulseG);
		const bigMult = new Text({
			text: '1.00x', style: {
				fontFamily: 'DynaPuff', fontSize: 58, fontWeight: '700', fill: 0xffffff,
				stroke: { color: 0x05351b, width: 9 },
			},
		});
		bigMult.anchor.set(0.5); bigMult.x = centreX; bigMult.y = FRAME + 34;
		title.visible = false;
		const chip = new Text({
			text: '', style: { fontFamily: 'IBM Plex Mono', fontSize: 13, fontWeight: '600', fill: 0x052012 },
		});
		chip.anchor.set(0, 0.5);
		ov.addChild(bigMult, chip);

		// chart geometry inside the board area
		const padL = FRAME + 10, right = FRAME + BOARD_W - 66, padT = FRAME + 64, bottom = FRAME + BOARD_H - 10;
		const iw = right - padL, ih = bottom - padT;
		const CW = 16, GAP = 7, slot = CW + GAP;
		const maxVis = Math.floor(iw / slot) - 1;

		const completed: number[][] = [];
		let live: { open: number; high: number; low: number; price: number } | null = null;
		let yLo = 0.6, yHi = 2.0;

		const draw = () => {
			const cur = completed.length;
			const xLast = padL + iw - CW;
			const xOf = (i: number) => xLast - (cur - i) * slot;
			// auto-scale to the visible window
			let lo = Infinity, hi = -Infinity;
			for (let i = Math.max(0, cur - maxVis); i < cur; i++) { lo = Math.min(lo, completed[i][2] / 100); hi = Math.max(hi, completed[i][1] / 100); }
			if (live) { lo = Math.min(lo, live.low / 100); hi = Math.max(hi, live.high / 100); }
			if (!isFinite(lo)) { lo = 0.85; hi = 1.35; }
			const pv = (hi - lo) * 0.14 + 0.04; lo = Math.max(0, lo - pv); hi += pv;
			yLo += (lo - yLo) * 0.2; yHi += (hi - yHi) * 0.2;
			const yOf = (m: number) => padT + ih - ((m - yLo) / (yHi - yLo)) * ih;

			gridG.clear();
			const span = yHi - yLo;
			const step = span > 400 ? 100 : span > 160 ? 50 : span > 60 ? 20 : span > 24 ? 10 : span > 10 ? 5 : span > 4 ? 2 : span > 2 ? 1 : 0.5;
			for (let m = Math.ceil(yLo / step) * step; m < yHi; m += step) {
				const yy = yOf(m);
				gridG.moveTo(padL, yy).lineTo(padL + iw, yy).stroke({ width: 1, color: 0x1b2030 });
			}

			candleG.clear();
			const dc = (i: number, o: number, h: number, l: number, c: number) => {
				const bx = xOf(i); if (bx + CW < padL) return;
				const col = c >= o ? GREEN : RED, cxp = bx + CW / 2;
				const yO = yOf(o / 100), yC = yOf(c / 100), yH = yOf(h / 100), yL = yOf(l / 100);
				const top = Math.min(yO, yC), bh = Math.max(3, Math.abs(yC - yO));
				candleG.roundRect(bx - 2, top - 2, CW + 4, bh + 4, 4).fill({ color: col, alpha: 0.16 });
				candleG.moveTo(cxp, yH).lineTo(cxp, yL).stroke({ width: 2.5, color: col, alpha: 0.95 });
				candleG.roundRect(bx, top, CW, bh, 3).fill(col);
			};
			for (let i = 0; i < cur; i++) dc(i, completed[i][0], completed[i][1], completed[i][2], completed[i][3]);
			if (live) dc(cur, live.open, live.high, live.low, live.price);

			pulseG.clear();
			const price = live ? live.price : (cur ? completed[cur - 1][3] : 100);
			const py = yOf(price / 100);
			for (let px = padL; px < padL + iw + 20; px += 14) pulseG.moveTo(px, py).lineTo(px + 7, py).stroke({ width: 2, color: CYAN, alpha: 0.65 });
			const dot = 4 + Math.sin(this.time / 140) * 1.6;
			pulseG.circle(xLast + CW / 2, py, dot + 5).fill({ color: CYAN, alpha: 0.18 });
			pulseG.circle(xLast + CW / 2, py, dot).fill(CYAN);
			pulseG.roundRect(padL + iw + 4, py - 12, 80, 24, 7).fill(CYAN);
			chip.text = `${(price / 100).toFixed(2)}x`; chip.position.set(padL + iw + 12, py);

			const mm = price / 100;
			bigMult.text = `${mm.toFixed(mm >= 100 ? 0 : 2)}x`;
			bigMult.style.fontSize = 50 + Math.min(44, Math.log(Math.max(1, mm)) * 9);
			bigMult.style.fill = live ? 0xffffff : (moon ? GOLD : GREEN);
		};

		// generate the price run and play it candle-by-candle
		const seq = this.genPriceRun(peakX);
		for (let k = 0; k < seq.length; k++) {
			const [o, h, l, c] = seq[k];
			const isRugC = c < o * 0.5;
			const pts = tickPath(o, h, l, c, isRugC, Math.random);
			live = { open: o, high: o, low: o, price: o };
			const formMs = 760;   // match the original crash game's 800ms candle pace
			let tk = 0;
			await this.tween(formMs, (t) => t, (v) => {
				const segs = pts.length - 1, ft = v * segs, si = Math.min(segs - 1, Math.floor(ft));
				const price = pts[si] + (pts[si + 1] - pts[si]) * smoothStep(ft - si);
				live!.price = price;
				live!.high = Math.max(live!.high, price);
				live!.low = Math.min(live!.low, price);
				draw();
				if (performance.now() - tk > 50) { sfx.candleTick(); tk = performance.now(); }
			});
			completed.push([o, h, l, c]);
			live = null;
			draw();
			if (isRugC) { this.shake = 360; sfx.rug?.(); }
			else sfx.candle?.(c >= o);
		}

		// SETTLE: crown the peak
		this.shake = 300;
		const peakY = FRAME + 34;
		this.burst(centreX, peakY, moon ? GOLD : GREEN, 26, ov);
		for (let i = 0; i < 20; i++) setTimeout(() => this.burst(Math.random() * LW, FRAME + 80, i % 2 ? GOLD : GREEN, 3, ov), i * 50);
		sfx.win();

		const tag = new Text({
			text: moon ? 'MOON!' : 'JACKPOT', style: {
				fontFamily: 'DynaPuff', fontSize: 40, fontWeight: '700', fill: moon ? GOLD : GREEN,
				stroke: { color: 0x05351b, width: 8 },
			},
		});
		tag.anchor.set(0.5); tag.x = centreX; tag.y = FRAME + BOARD_H / 2 - 28; tag.scale.set(0);
		ov.addChild(tag);
		await this.tween(400, outBack, (v) => tag.scale.set(v));

		const winMicro = Math.round(betMicro * peakX);
		const payout = new Text({
			text: fmtMoney(winMicro), style: {
				fontFamily: 'DynaPuff', fontSize: 52, fontWeight: '700', fill: 0xffffff,
				stroke: { color: 0x05351b, width: 9 },
			},
		});
		payout.anchor.set(0.5); payout.x = centreX; payout.y = FRAME + BOARD_H / 2 + 28; payout.alpha = 0;
		ov.addChild(payout);
		await this.tween(520, outCubic, (v) => { payout.alpha = v; payout.text = fmtMoney(Math.round(winMicro * v)); });
		await sleep(1700);

		const parts: { alpha: number }[] = [veil, title, bigMult, chip, gridG, candleG, pulseG, tag, payout];
		await this.tween(320, inCubic, (v) => { for (const p of parts) p.alpha = (p === veil ? 0.94 : 1) * (1 - v); });
		veil.destroy(); title.destroy(); bigMult.destroy(); chip.destroy();
		gridG.destroy(); candleG.destroy(); pulseG.destroy(); tag.destroy(); payout.destroy();
		for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
			const s = this.sprites[c][r];
			if (s) { s.destroy(); this.sprites[c][r] = null; }
		}
		this.firstSpin = true;
		return winMicro;
	}

	/** Build a REALISTIC OHLC price run (hundredths of 1.00x) to peakX. Each candle
	 * carries a chop return sampled from the crash game's weighted distribution
	 * (mostly small red/green moves — the sideways grind) plus a drift that is tiny
	 * early and large late, so the chart meanders, then BOOMS with big green candles
	 * into the peak. Non-moon runs end on a red rug candle; the peak is still banked. */
	private genPriceRun(peakX: number): number[][] {
		const target = Math.round(peakX * 100);
		const moon = peakX >= 50;
		// fewer candles now that each forms slowly (~760ms) so the run stays ~10-13s
		const n = Math.min(16, Math.max(11, Math.round(10 + Math.log(peakX) * 2)));

		// realistic chop: per-candle multiplier weighted like ambient.ts CANDLE_OUTCOMES,
		// trimmed to the non-rug range (roughly balanced so it grinds sideways, not down).
		const CHOP: [number, number][] = [
			[0.82, 150], [0.90, 150], [0.96, 120], [1.00, 110],
			[1.06, 120], [1.12, 120], [1.20, 70], [1.35, 24],
		];
		const chopTot = CHOP.reduce((s, [, w]) => s + w, 0);
		const sampleChop = () => {
			let roll = Math.random() * chopTot;
			for (const [r, w] of CHOP) { roll -= w; if (roll <= 0) return Math.log(r); }
			return 0;
		};

		// chop is strong during the grind, damped during the boom so big green dominates
		const chops: number[] = [];
		for (let i = 0; i < n; i++) chops.push(sampleChop() * (i < n * 0.62 ? 1 : 0.35));
		const sumChop = chops.reduce((a, b) => a + b, 0);

		// boom weights: the climb is back-loaded (p^2.8) → flat start, explosive finish
		const bw = (i: number) => Math.pow(i / (n - 1), 2.8);
		let sumBW = 0; for (let i = 0; i < n; i++) sumBW += bw(i);
		const drift = Math.log(target / 100) - sumChop;   // remaining lift to distribute

		const candles: number[][] = [];
		let price = 100;
		for (let i = 0; i < n; i++) {
			const open = price;
			const logRet = chops[i] + drift * (bw(i) / sumBW);
			let close = Math.round(open * Math.exp(logRet));
			close = Math.max(55, close);                  // allow dips, never to zero
			const spread = Math.max(2, Math.abs(close - open));
			const high = Math.max(open, close) + Math.round(spread * Math.random() * 0.5);
			const low = Math.max(40, Math.min(open, close) - Math.round(spread * Math.random() * 0.4));
			candles.push([open, high, low, close]);
			price = close;
		}
		// land the peak exactly on target (the banked jackpot)
		const last = candles[candles.length - 1];
		last[3] = target; last[1] = Math.max(last[1], target);
		// non-moon drama: a red rug candle dumping back down after the peak
		if (!moon) candles.push([target, Math.round(target * 1.01), 108, 114]);
		return candles;
	}

	private shatterRow(r: number, layer: Container) {
		for (let c = 0; c < COLS; c++) {
			const sp = this.sprites[c][r];
			if (!sp) continue;
			this.sprites[c][r] = null;
			const px = sp.x + FRAME, py = sp.y + FRAME; // board-local -> root (overlay) coords
			this.burst(px, py, 0xffffff, 6, layer);
			this.burst(px, py, GREEN, 4, layer);
			void this.tween(220, inCubic, (v) => { sp.scale.set(Math.max(0.01, 1 - v)); sp.alpha = 1 - v; sp.rotation = v * 0.6; })
				.then(() => sp.destroy());
		}
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
