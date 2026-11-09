// GOD CANDLE — client-side spin resolver (prototype "mock RGS").
// Produces a fully-resolved SpinResult event book that the board REPLAYS,
// mirroring Engine's architecture: the server decides, the front end presents.
// The real build swaps this for pre-baked books served by the RGS; the
// SpinResult shape is designed to match what those books will contain.

import {
	COLS, ROWS, PAYS, WEIGHTS, ORB_VALUES, SCATTER_PAY, BEAR_FACTOR_PER, MONEYGUN_PRIZES, VAULT_PRIZES,
	MYSTERY_MULTS, MYSTERY_JACKPOT_CHANCE, payTier,
	type Cell, type SymbolId, type PayingSymbol,
} from './paytable';

export interface WinGroup {
	sym: PayingSymbol;
	cells: [number, number][]; // [col, row]
	count: number;
	winMicro: number;
}

export interface OrbCell {
	col: number;
	row: number;
	value: number;
}

export interface NewCell {
	col: number;
	row: number;
	cell: Cell;
}

export interface TumbleStep {
	/** Full grid state after this drop settles. grid[col][row], row 0 = top. */
	grid: Cell[][];
	/** Cells that are new in this step (all 30 on step 0). */
	newCells: NewCell[];
	/** Wins present in this grid; empty = sequence ends after this step. */
	wins: WinGroup[];
	/** Orbs that landed NEW in this step. */
	orbs: OrbCell[];
	stepWinMicro: number;
}

export interface SpinResult {
	betMicro: number;
	steps: TumbleStep[];
	/** Sum of every orb that landed during the sequence. */
	orbTotal: number;
	/** Multiplier actually applied to the tumble win (0 = none). */
	appliedMult: number;
	baseWinMicro: number;     // tumble wins before multiplier
	scatterCount: number;
	scatterWinMicro: number;
	grossWinMicro: number;    // tumble×mult + scatter, BEFORE the bear penalty
	bearCount: number;        // bears on the settled grid (each halves the win)
	bearFactor: number;       // 0.5^bearCount applied to the gross win
	moneygunPrizes: number[]; // per money-gun cash prize (micro), sprayed on top
	moneygunWinMicro: number; // sum of the money-gun prizes (bear can't touch it)
	vaultPrizes: number[];    // per bank-vault cash prize (micro), unlocked on top
	vaultWinMicro: number;    // sum of the vault prizes (bear-immune)
	candleReveal: { col: number; row: number; mult: number; masked: boolean }[]; // mystery candles
	candlePrizeMicro: number; // sum of revealed candle multipliers × bet (bear-immune)
	mysteryJackpot: boolean;  // a candle revealed the jackpot → the full price-action run
	totalWinMicro: number;    // net = round(gross × bearFactor) + moneygun + candlePrize
	triggersFreeSpins: boolean;
	retrigger: boolean;
}

const WEIGHT_TOTAL = WEIGHTS.reduce((a, [, w]) => a + w, 0);
const ORB_TOTAL = ORB_VALUES.reduce((a, [, w]) => a + w, 0);
const MYSTERY_TOT = MYSTERY_MULTS.reduce((a, [, w]) => a + w, 0);

/** A god-candle's hidden multiplier (× bet), or -1 for the mystery jackpot. */
function drawMystery(): number {
	if (Math.random() < MYSTERY_JACKPOT_CHANCE) return -1;
	let r = Math.random() * MYSTERY_TOT;
	for (const [v, w] of MYSTERY_MULTS) { r -= w; if (r <= 0) return v; }
	return 0.15;
}

function drawSymbol(noScatter: boolean): Cell {
	for (;;) {
		let r = Math.random() * WEIGHT_TOTAL;
		for (const [sym, w] of WEIGHTS) {
			r -= w;
			if (r < 0) {
				if (sym === 'scatter' && noScatter) break; // redraw
				if (sym === 'orb') return { sym, orb: drawOrbValue() };
				if (sym === 'scatter') return { sym, mystery: drawMystery(), masked: Math.random() < 0.5 };
				return { sym };
			}
		}
	}
}

function drawOrbValue(): number {
	let r = Math.random() * ORB_TOTAL;
	for (const [v, w] of ORB_VALUES) {
		r -= w;
		if (r < 0) return v;
	}
	return 2;
}

function detectWins(grid: Cell[][], betMicro: number): WinGroup[] {
	const bySym = new Map<PayingSymbol, [number, number][]>();
	for (let c = 0; c < COLS; c++) {
		for (let r = 0; r < ROWS; r++) {
			const sym = grid[c][r].sym;
			if (sym === 'scatter' || sym === 'orb' || sym === 'bear' || sym === 'moneygun' || sym === 'vault') continue;
			const list = bySym.get(sym as PayingSymbol) ?? [];
			list.push([c, r]);
			bySym.set(sym as PayingSymbol, list);
		}
	}
	const wins: WinGroup[] = [];
	for (const [sym, cells] of bySym) {
		if (cells.length >= 8) {
			const mult = PAYS[sym][payTier(cells.length)];
			wins.push({ sym, cells, count: cells.length, winMicro: Math.round(betMicro * mult) });
		}
	}
	// deterministic presentation order: biggest win first
	wins.sort((a, b) => b.winMicro - a.winMicro);
	return wins;
}

function countScatters(grid: Cell[][]): number {
	let n = 0;
	for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) if (grid[c][r].sym === 'scatter') n++;
	return n;
}

function countBears(grid: Cell[][]): number {
	let n = 0;
	for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) if (grid[c][r].sym === 'bear') n++;
	return n;
}

const MONEYGUN_TOT = MONEYGUN_PRIZES.reduce((a, [, w]) => a + w, 0);
function drawMoneygunPrize(): number {
	let roll = Math.random() * MONEYGUN_TOT;
	for (const [v, w] of MONEYGUN_PRIZES) { roll -= w; if (roll <= 0) return v; }
	return 2;
}
/** Each money gun on the grid sprays a cash prize (× bet). Returns per-gun values. */
function moneygunPrizes(grid: Cell[][], betMicro: number): number[] {
	const out: number[] = [];
	for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
		if (grid[c][r].sym === 'moneygun') out.push(Math.round(betMicro * drawMoneygunPrize()));
	}
	return out;
}

const VAULT_TOT = VAULT_PRIZES.reduce((a, [, w]) => a + w, 0);
function drawVaultPrize(): number {
	let roll = Math.random() * VAULT_TOT;
	for (const [v, w] of VAULT_PRIZES) { roll -= w; if (roll <= 0) return v; }
	return 10;
}
/** Each bank vault on the grid unlocks a big cash prize (× bet). */
function vaultPrizes(grid: Cell[][], betMicro: number): number[] {
	const out: number[] = [];
	for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
		if (grid[c][r].sym === 'vault') out.push(Math.round(betMicro * drawVaultPrize()));
	}
	return out;
}

function collectOrbs(cells: NewCell[]): OrbCell[] {
	return cells
		.filter((n) => n.cell.sym === 'orb')
		.map((n) => ({ col: n.col, row: n.row, value: n.cell.orb! }));
}

/** GOD CANDLE JACKPOT outcome: the peak multiplier the candle climbs to before it
 * rugs. Heavy-tailed (rugs.fun style): most runs peak low, rare moon shots to 1000x.
 * peakX follows P(peak ≥ x) ≈ k/x, inverse-sampled, clamped to [1.5, 1000]. */
export function godCandlePeak(): number {
	const u = Math.random();
	const peak = Math.min(1000, Math.max(1.5, 0.92 / (1 - u)));
	return Math.round(peak * 100) / 100;
}

/** Cosmetic resting grid shown before the first spin: pays symbols + 1-2 live
 * god-candle scatters so the fluctuating candle is visible on the board. No orbs. */
export function displayGrid(): Cell[][] {
	const grid: Cell[][] = [];
	for (let c = 0; c < COLS; c++) {
		grid[c] = [];
		for (let r = 0; r < ROWS; r++) {
			let cell = drawSymbol(true);
			while (cell.sym === 'orb') cell = drawSymbol(true);
			grid[c][r] = cell;
		}
	}
	// sprinkle 1-2 scatters on distinct columns so the live candle shows at rest
	const n = 1 + (Math.random() < 0.5 ? 1 : 0);
	const cols = [0, 1, 2, 3, 4, 5].sort(() => Math.random() - 0.5).slice(0, n);
	for (const c of cols) grid[c][Math.floor(Math.random() * ROWS)] = { sym: 'scatter' };
	return grid;
}

export interface SpinOptions {
	/** Force a bonus-triggering grid (bonus buy). */
	forceBonus?: boolean;
	/** Dev preview (?testwin=rocket): plant a guaranteed 8-count win of this symbol. */
	forceWin?: PayingSymbol;
	/** Inside free spins: 3+ scatters retrigger instead of triggering. */
	freeSpin?: boolean;
	/** Free-spins running total multiplier BEFORE this spin. */
	fsTotalMult?: number;
}

export function spin(betMicro: number, opts: SpinOptions = {}): SpinResult {
	// --- initial drop ---
	const grid: Cell[][] = [];
	const initial: NewCell[] = [];
	for (let c = 0; c < COLS; c++) {
		grid[c] = [];
		for (let r = 0; r < ROWS; r++) {
			grid[c][r] = drawSymbol(false);
			initial.push({ col: c, row: r, cell: grid[c][r] });
		}
	}
	if (opts.forceWin) {
		const spots: [number, number][] = [];
		for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) spots.push([c, r]);
		spots.sort(() => Math.random() - 0.5);
		for (const [c, r] of spots.slice(0, 8)) grid[c][r] = { sym: opts.forceWin };
		for (const n of initial) n.cell = grid[n.col][n.row];
	}
	if (opts.forceBonus) {
		// plant exactly 4 scatters on distinct columns
		for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
			if (grid[c][r].sym === 'scatter') grid[c][r] = { sym: 'coinT' };
		}
		const cols = [0, 1, 2, 3, 4, 5].sort(() => Math.random() - 0.5).slice(0, 4);
		for (const c of cols) {
			const r = Math.floor(Math.random() * ROWS);
			grid[c][r] = { sym: 'scatter' };
		}
		for (const n of initial) n.cell = grid[n.col][n.row];
	}

	const steps: TumbleStep[] = [];
	let baseWin = 0;
	let orbTotal = 0;
	let newCells = initial;

	// --- tumble loop ---
	for (;;) {
		const wins = detectWins(grid, betMicro);
		const orbs = collectOrbs(newCells);
		for (const o of orbs) orbTotal += o.value;
		const stepWin = wins.reduce((a, w) => a + w.winMicro, 0);
		baseWin += stepWin;
		steps.push({
			grid: grid.map((col) => col.map((cell) => ({ ...cell }))),
			newCells,
			wins,
			orbs,
			stepWinMicro: stepWin,
		});
		if (!wins.length) break;

		// remove winning cells, collapse, refill from the top
		const removed = new Set<number>();
		for (const w of wins) for (const [c, r] of w.cells) removed.add(c * ROWS + r);
		newCells = [];
		for (let c = 0; c < COLS; c++) {
			const kept = grid[c].filter((_, r) => !removed.has(c * ROWS + r));
			const need = ROWS - kept.length;
			const fresh: Cell[] = [];
			for (let i = 0; i < need; i++) fresh.push(drawSymbol(false));
			grid[c] = [...fresh, ...kept];
			for (let r = 0; r < need; r++) newCells.push({ col: c, row: r, cell: grid[c][r] });
		}
	}

	// --- settle ---
	const scatterCount = countScatters(grid);
	let appliedMult = 0;
	let tumbleWin = baseWin;
	if (baseWin > 0 && orbTotal > 0) {
		appliedMult = opts.freeSpin ? (opts.fsTotalMult ?? 0) + orbTotal : orbTotal;
		tumbleWin = Math.round(baseWin * appliedMult);
	}
	const scatterWin =
		!opts.freeSpin && scatterCount >= 4
			? Math.round(betMicro * (SCATTER_PAY[Math.min(scatterCount, 6)] ?? SCATTER_PAY[6]))
			: 0;

	// BEAR MARKET: each bear on the settled grid halves the spin win.
	const grossWin = tumbleWin + scatterWin;
	const bearCount = countBears(grid);
	const bearFactor = bearCount > 0 ? Math.pow(BEAR_FACTOR_PER, bearCount) : 1;
	const netPayWin = bearCount > 0 ? Math.round(grossWin * bearFactor) : grossWin;

	// MONEY GUN: each gun sprays a cash prize on top (not touched by the bear).
	const gunPrizes = moneygunPrizes(grid, betMicro);
	const moneygunWin = gunPrizes.reduce((a, b) => a + b, 0);

	// BANK VAULT: each vault unlocks a big cash prize on top (bear-immune).
	const vPrizes = vaultPrizes(grid, betMicro);
	const vaultWin = vPrizes.reduce((a, b) => a + b, 0);

	// MYSTERY CANDLE: every god-candle reveals its hidden multiplier (× bet). Bear-immune.
	// One revealing the jackpot (-1) fires the full price-action run instead of a flat pay.
	const candleReveal: { col: number; row: number; mult: number; masked: boolean }[] = [];
	let candlePrize = 0;
	let mysteryJackpot = false;
	for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
		const cell = grid[c][r];
		if (cell.sym !== 'scatter') continue;
		const mult = cell.mystery ?? 0;
		candleReveal.push({ col: c, row: r, mult, masked: !!cell.masked });
		if (mult < 0) mysteryJackpot = true;
		else candlePrize += Math.round(betMicro * mult);
	}

	return {
		betMicro,
		steps,
		orbTotal,
		appliedMult,
		baseWinMicro: baseWin,
		scatterCount,
		scatterWinMicro: scatterWin,
		grossWinMicro: grossWin,
		bearCount,
		bearFactor,
		moneygunPrizes: gunPrizes,
		moneygunWinMicro: moneygunWin,
		vaultPrizes: vPrizes,
		vaultWinMicro: vaultWin,
		candleReveal,
		candlePrizeMicro: candlePrize,
		mysteryJackpot,
		totalWinMicro: netPayWin + moneygunWin + vaultWin + candlePrize,
		triggersFreeSpins: !opts.freeSpin && scatterCount >= 4,
		retrigger: !!opts.freeSpin && scatterCount >= 3,
	};
}
