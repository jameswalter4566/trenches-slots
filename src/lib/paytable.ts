// GOD CANDLE — symbol set, pays and draw weights.
// Prototype math: these weights drive the client-side sim in sim.ts. The final
// Engine build replaces sim.ts with pre-baked books from the Python math layer;
// this file stays the single source of truth for the FE presentation order.

export const COLS = 6;
export const ROWS = 5;

export type SymbolId =
	| 'goldbar' | 'bull' | 'rocket' | 'whale' | 'frog' | 'diamond' | 'moon'  // high pays
	| 'terminal'                                            // mid-low filler
	| 'coinG' | 'coinP' | 'coinB' | 'coinT'                 // low pays (coins)
	| 'scatter'                                             // GOD CANDLE scatter
	| 'orb'                                                 // multiplier orb
	| 'bear'                                                // BEAR MARKET — dumps the win
	| 'moneygun'                                            // MONEY GUN — sprays a cash prize
	| 'vault';                                              // BANK VAULT — unlocks a big cash prize

export interface Cell {
	sym: SymbolId;
	orb?: number;     // multiplier value when sym === 'orb'
	mystery?: number; // god-candle hidden multiplier (× bet); -1 = mystery jackpot
	masked?: boolean; // god-candle shows '?' until revealed
}

export type PayingSymbol = Exclude<SymbolId, 'scatter' | 'orb' | 'bear' | 'moneygun' | 'vault'>;

// Each bear on the settled grid halves the spin win (bull pumps, bear dumps).
export const BEAR_FACTOR_PER = 0.5;

// Each money gun sprays a cash prize (× bet). Weighted toward small, rare big.
export const MONEYGUN_PRIZES: [number, number][] = [
	[0.3, 240], [0.5, 180], [1, 80], [2, 25], [3, 8], [5, 2],
];

// The bank vault cracks open for a cash prize (× bet) — rarer, heftier than the gun.
export const VAULT_PRIZES: [number, number][] = [
	[2, 200], [5, 120], [10, 50], [25, 15], [50, 4], [100, 1],
];

// MYSTERY CANDLE: every god-candle tile hides a multiplier (× bet), revealed with
// the candle animation. Mostly tiny so it plays often; rare big. A separate small
// chance makes a candle the MYSTERY JACKPOT (value -1 -> the full price-action run).
export const MYSTERY_MULTS: [number, number][] = [
	[0.1, 340], [0.15, 230], [0.25, 110], [0.5, 40], [1, 14], [2, 3],
];
export const MYSTERY_JACKPOT_CHANCE = 0.010; // per candle

// Pays as multiples of total bet for counts [8-9, 10-11, 12+] anywhere on the grid.
export const PAYS: Record<PayingSymbol, [number, number, number]> = {
	goldbar: [1,    2.6,  6.1],
	bull:    [1.3,  3.1,  7.7],
	rocket:  [0.92, 2.1,  5.1],
	whale:   [0.4,  1,    2.5],   // retired (not in WEIGHTS)
	frog:    [0.3,  0.7,  2],     // retired
	diamond: [0.095, 0.24, 0.68], // low pay (real art)
	moon:    [0.15, 0.4,  1.3],   // retired
	terminal:[0.073, 0.18, 0.54], // low pay (real art)
	coinG:   [0.062, 0.15, 0.46],
	coinP:   [0.045, 0.115, 0.35],
	coinB:   [0.036, 0.09, 0.27],
	coinT:   [0.03,  0.075, 0.2],
};

export function payTier(count: number): 0 | 1 | 2 {
	return count >= 12 ? 2 : count >= 10 ? 1 : 0;
}

// Scatter pays (multiples of bet) for 4 / 5 / 6+ god candles.
export const SCATTER_PAY: Record<number, number> = { 4: 3, 5: 5, 6: 100 };
export const FREE_SPINS_AWARD = 15;
export const FS_RETRIGGER_SPINS = 5;
export const BONUS_BUY_COST = 100; // × bet

// Per-cell draw weights — REAL distribution tuned for a ~96.5% RTP (house edge).
// Low-pay fillers (coins) dominate so most spins lose; the animated high-pays
// (goldbar/rocket/bull) and feature symbols are rarer. Retune with tools/rtp.ts.
// Roster: real-art diamond + clean colored coins as low fillers, animated
// goldbar/bull/rocket/terminal as higher pays, + features. The ugly emoji
// placeholders (whale/frog/moon) are removed. 8 pay symbols keeps the grid
// diluted enough for a real ~96.5% RTP. Tuned via tools/rtp.ts.
export const WEIGHTS: [SymbolId, number][] = [
	// ONLY real animation-pack tiles + jackpot candle. No drawn coins/whale/frog/moon.
	// BEAR is the common grid-filler: it DUMPS wins, so a board full of bears is
	// self-limiting (keeps RTP sane). Orb is rare (only multiplies in free spins).
	['bear', 255],       // DILUTION — common, dumps the win (bear market everywhere)
	['diamond', 90],     // low pay (real art)
	['terminal', 82],    // low pay (real art)
	['goldbar', 36],     // high pays - rarer
	['rocket', 34],
	['bull', 32],
	['orb', 14],         // free-spins multiplier (rare so FS can't run away)
	['scatter', 11],     // mystery candle / jackpot
	['moneygun', 4],     // bonus cash
	['vault', 2],        // rare big bonus
];

// Orb multiplier values and weights (sum applied to the tumble-sequence win).
export const ORB_VALUES: [number, number][] = [
	[2, 200], [3, 160], [4, 120], [5, 100], [6, 80],
	[8, 60], [10, 50], [12, 40], [15, 30], [20, 24],
	[25, 20], [50, 12], [100, 6], [250, 3], [500, 2],
];

// Presentation metadata the board uses to draw each symbol.
export const SYMBOL_META: Record<SymbolId, { glyph: string; tile: number; edge: number; label: string }> = {
	goldbar: { glyph: '\u{1F947}', tile: 0x4a3a12, edge: 0x30250b, label: 'GOLD BAR' },
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
	terminal:{ glyph: '\u{1F4C8}', tile: 0x16263a, edge: 0x0c1824, label: 'TERMINAL' },
	scatter: { glyph: '',          tile: 0x113322, edge: 0x0a2015, label: 'GOD CANDLE' },
	orb:     { glyph: '',          tile: 0x3d3414, edge: 0x27210c, label: 'ORB' },
	bear:    { glyph: '\u{1F43B}', tile: 0x4a1d1d, edge: 0x301212, label: 'BEAR' },
	moneygun:{ glyph: '\u{1F4B5}', tile: 0x16401f, edge: 0x0c2814, label: 'MONEY GUN' },
	vault:   { glyph: '\u{1F3E6}', tile: 0x2a3340, edge: 0x1a2029, label: 'VAULT' },
};

export const COIN_COLORS: Record<string, { face: number; rim: number; glyph: number }> = {
	coinG: { face: 0xf7c843, rim: 0xb8860b, glyph: 0x7a5200 },
	coinP: { face: 0xb479ff, rim: 0x7b3fd1, glyph: 0x45207d },
	coinB: { face: 0x5aa2ff, rim: 0x2960c4, glyph: 0x143a7d },
	coinT: { face: 0x3ee6c2, rim: 0x14a384, glyph: 0x0a614e },
};
