// GOD CANDLE — symbol set, pays and draw weights.
// Prototype math: these weights drive the client-side sim in sim.ts. The final
// Engine build replaces sim.ts with pre-baked books from the Python math layer;
// this file stays the single source of truth for the FE presentation order.

export const COLS = 6;
export const ROWS = 5;

export type SymbolId =
	| 'bull' | 'rocket' | 'whale' | 'frog' | 'diamond' | 'moon'  // high pays
	| 'coinG' | 'coinP' | 'coinB' | 'coinT'                 // low pays (coins)
	| 'scatter'                                             // GOD CANDLE scatter
	| 'orb';                                                // multiplier orb

export interface Cell {
	sym: SymbolId;
	orb?: number; // multiplier value when sym === 'orb'
}

export type PayingSymbol = Exclude<SymbolId, 'scatter' | 'orb'>;

// Pays as multiples of total bet for counts [8-9, 10-11, 12+] anywhere on the grid.
export const PAYS: Record<PayingSymbol, [number, number, number]> = {
	bull:    [15,  40,  80],
	rocket:  [10,  25,  50],
	whale:   [2.5, 10,  25],
	frog:    [2,   5,   15],
	diamond: [1.5, 2,   12],
	moon:    [1,   1.5, 10],
	coinG:   [0.8, 1.2, 8],
	coinP:   [0.5, 1,   5],
	coinB:   [0.4, 0.9, 4],
	coinT:   [0.25, 0.75, 2],
};

export function payTier(count: number): 0 | 1 | 2 {
	return count >= 12 ? 2 : count >= 10 ? 1 : 0;
}

// Scatter pays (multiples of bet) for 4 / 5 / 6+ god candles.
export const SCATTER_PAY: Record<number, number> = { 4: 3, 5: 5, 6: 100 };
export const FREE_SPINS_AWARD = 15;
export const FS_RETRIGGER_SPINS = 5;
export const BONUS_BUY_COST = 100; // × bet

// Per-cell draw weights for the prototype sim.
export const WEIGHTS: [SymbolId, number][] = [
	['coinT', 180],
	['coinB', 160],
	['coinP', 140],
	['coinG', 120],
	['moon', 80],
	['diamond', 70],
	['frog', 60],
	['whale', 50],
	['rocket', 40],
	['bull', 30],
	['scatter', 20],
	['orb', 14],
];

// Orb multiplier values and weights (sum applied to the tumble-sequence win).
export const ORB_VALUES: [number, number][] = [
	[2, 200], [3, 160], [4, 120], [5, 100], [6, 80],
	[8, 60], [10, 50], [12, 40], [15, 30], [20, 24],
	[25, 20], [50, 12], [100, 6], [250, 3], [500, 2],
];

// Presentation metadata the board uses to draw each symbol.
export const SYMBOL_META: Record<SymbolId, { glyph: string; tile: number; edge: number; label: string }> = {
	bull:    { glyph: '\u{1F402}', tile: 0x4a2d1d, edge: 0x301c12, label: 'BULL' },
	rocket:  { glyph: '\u{1F680}', tile: 0x3a2d55, edge: 0x241b38, label: 'ROCKET' },
	whale:   { glyph: '\u{1F40B}', tile: 0x1d3a55, edge: 0x122538, label: 'WHALE' },
	frog:    { glyph: '\u{1F438}', tile: 0x1d4a2f, edge: 0x11301d, label: 'FROG' },
	diamond: { glyph: '\u{1F48E}', tile: 0x1d4550, edge: 0x112d35, label: 'DIAMOND' },
	moon:    { glyph: '\u{1F315}', tile: 0x4a4420, edge: 0x302c12, label: 'MOON' },
	coinG:   { glyph: '$',         tile: 0x4a3a16, edge: 0x30250c, label: 'GOLD' },
	coinP:   { glyph: '▲',    tile: 0x3c2050, edge: 0x271334, label: 'PURP' },
	coinB:   { glyph: '%',         tile: 0x1b2d52, edge: 0x101c36, label: 'BLUE' },
	coinT:   { glyph: '✦',    tile: 0x14433e, edge: 0x0b2b27, label: 'TEAL' },
	scatter: { glyph: '',          tile: 0x113322, edge: 0x0a2015, label: 'GOD CANDLE' },
	orb:     { glyph: '',          tile: 0x3d3414, edge: 0x27210c, label: 'ORB' },
};

export const COIN_COLORS: Record<string, { face: number; rim: number; glyph: number }> = {
	coinG: { face: 0xf7c843, rim: 0xb8860b, glyph: 0x7a5200 },
	coinP: { face: 0xb479ff, rim: 0x7b3fd1, glyph: 0x45207d },
	coinB: { face: 0x5aa2ff, rim: 0x2960c4, glyph: 0x143a7d },
	coinT: { face: 0x3ee6c2, rim: 0x14a384, glyph: 0x0a614e },
};
