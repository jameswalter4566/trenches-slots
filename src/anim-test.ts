// Standalone animation preview harness (served at /anim-test.html).
// Loads every *_win and *_idle strip the slicer produced and plays each in its
// own canvas so you can judge the motion in isolation as sheets are generated.

import { AnimatedSprite, Application, Assets, Container, Rectangle, Sprite, Texture } from 'pixi.js';

const SYMBOLS = [
	'goldbar', 'bull', 'bear', 'moneygun', 'rocket', 'whale', 'frog', 'diamond', 'moon',
	'coinG', 'coinP', 'coinB', 'coinT', 'scatter', 'orb',
];
const KINDS = ['win', 'idle'] as const;

const gridEl = document.getElementById('grid')!;
const bgSel = document.getElementById('bg') as HTMLSelectElement;
const stages: { app: Application; anim?: AnimatedSprite }[] = [];

interface SheetMeta { frames: number; fw: number; fh: number; fps: number; anchorX?: number; anchorY?: number; bodyFrac?: number }

async function loadStrip(sym: string, kind: string): Promise<{ frames: Texture[]; meta: SheetMeta } | null> {
	try {
		const res = await fetch(`/symbols/anim/${sym}_${kind}.json`);
		if (!res.ok) return null;
		const meta = (await res.json()) as SheetMeta;
		const base = await Assets.load<Texture>(`/symbols/anim/${sym}_${kind}.png`);
		const frames: Texture[] = [];
		for (let i = 0; i < meta.frames; i++) {
			frames.push(new Texture({ source: base.source, frame: new Rectangle(i * meta.fw, 0, meta.fw, meta.fh) }));
		}
		return { frames, meta };
	} catch {
		return null;
	}
}

async function loadStatic(sym: string): Promise<Texture | null> {
	try {
		return await Assets.load<Texture>(`/symbols/${sym}.png`);
	} catch {
		return null;
	}
}

function checkerCss(): string {
	return 'repeating-conic-gradient(#2a2f3d 0% 25%, #1a1d26 0% 50%) 50% / 24px 24px';
}

async function build() {
for (const sym of SYMBOLS) {
	for (const kind of KINDS) {
		const strip = await loadStrip(sym, kind);
		const staticTex = kind === 'win' ? await loadStatic(sym) : null;
		if (!strip && !staticTex) {
			// show a placeholder card only for the win slot so the set reads as a checklist
			if (kind === 'win') addMissingCard(sym);
			continue;
		}

		const card = document.createElement('div');
		card.className = 'card';
		const stage = document.createElement('div');
		stage.className = 'stage';
		card.appendChild(stage);

		const name = document.createElement('div');
		name.className = 'name';
		name.textContent = `${sym} · ${kind}`;
		const meta = document.createElement('div');
		meta.className = 'meta';
		meta.textContent = strip ? `${strip.meta.frames} frames @ ${strip.meta.fps}fps` : 'static only';
		card.append(name, meta);

		const row = document.createElement('div');
		row.className = 'row';
		card.appendChild(row);
		gridEl.appendChild(card);

		const app = new Application();
		await app.init({ width: 180, height: 180, backgroundAlpha: 0, antialias: true, resolution: 2, autoDensity: true });
		stage.appendChild(app.canvas);
		const holder = { app, anim: undefined as AnimatedSprite | undefined };
		stages.push(holder);

		const root = new Container();
		app.stage.addChild(root);
		root.x = 90; root.y = 90;

		if (strip) {
			const a = new AnimatedSprite(strip.frames);
			a.anchor.set(strip.meta.anchorX ?? 0.5, strip.meta.anchorY ?? 0.5);
			a.animationSpeed = strip.meta.fps / 60;
			const fw = a.texture.width, fh = a.texture.height;
			a.scale.set(strip.meta.bodyFrac ? 88 / (strip.meta.bodyFrac * fw) : 150 / Math.max(fw, fh));
			a.loop = true;
			a.play();
			root.addChild(a);
			holder.anim = a;

			const replay = document.createElement('button');
			replay.textContent = '▶ replay';
			replay.onclick = () => { a.gotoAndPlay(0); };
			row.appendChild(replay);

			const once = document.createElement('button');
			once.className = 'ghost';
			once.textContent = 'once';
			once.onclick = () => { a.loop = false; a.gotoAndPlay(0); a.onComplete = () => { a.loop = true; }; };
			row.appendChild(once);
		} else if (staticTex) {
			const sp = new Sprite(staticTex);
			sp.anchor.set(0.5);
			sp.scale.set(150 / Math.max(sp.texture.width, sp.texture.height));
			root.addChild(sp);
		}
	}
}
}

function addMissingCard(sym: string) {
	const card = document.createElement('div');
	card.className = 'card missing';
	card.innerHTML = `<div class="stage"></div><div class="name">${sym}</div><div class="meta">no sheet yet</div>`;
	gridEl.appendChild(card);
}

// background swatch control
function applyBg() {
	const v = bgSel.value;
	for (const s of stages) {
		const el = s.app.canvas.parentElement as HTMLElement;
		el.style.background = v === 'transparent' ? checkerCss() : v;
	}
}
bgSel.onchange = applyBg;

document.getElementById('playall')!.onclick = () => {
	for (const s of stages) s.anim?.gotoAndPlay(0);
};

void build().then(applyBg);
