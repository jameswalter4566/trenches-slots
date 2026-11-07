// Launch-URL context (studio.engine.io/docs/rgs). Reads every parameter the platform
// sends, with safe fallbacks, so the UI can honour currency, language, social mode and replay.
const params = new URLSearchParams(location.search);

export const session = {
	sessionID: params.get('sessionID') ?? '',
	rgsUrl: params.get('rgs_url') ?? '',
	lang: (params.get('lang') || 'en').toLowerCase(),
	currency: (params.get('currency') || 'USD').toUpperCase(),
	device: params.get('device') ?? 'desktop',
	social: params.get('social') === 'true',
	demo: params.get('demo') === 'true',
	replay: params.get('replay') === 'true',
	// replay-only params
	game: params.get('game') ?? '',
	version: params.get('version') ?? '',
	mode: params.get('mode') ?? '',
	event: params.get('event') ?? '',
	amount: params.get('amount') ? Number(params.get('amount')) : 0,
};

// Currency metadata per Engine's RGS doc: symbol, default decimals, symbol placement.
type Meta = { symbol: string; decimals: number; after?: boolean };
const CURRENCY: Record<string, Meta> = {
	USD: { symbol: '$', decimals: 2 }, CAD: { symbol: 'CA$', decimals: 2 },
	JPY: { symbol: '¥', decimals: 0 }, EUR: { symbol: '€', decimals: 2 },
	RUB: { symbol: '₽', decimals: 2 }, CNY: { symbol: 'CN¥', decimals: 2 },
	PHP: { symbol: '₱', decimals: 2 }, INR: { symbol: '₹', decimals: 2 },
	IDR: { symbol: 'Rp', decimals: 0 }, KRW: { symbol: '₩', decimals: 0 },
	BRL: { symbol: 'R$', decimals: 2 }, MXN: { symbol: 'MX$', decimals: 2 },
	DKK: { symbol: 'kr', decimals: 2, after: true }, PLN: { symbol: 'zł', decimals: 2, after: true },
	VND: { symbol: '₫', decimals: 0, after: true }, TRY: { symbol: '₺', decimals: 2 },
	CLP: { symbol: 'CLP', decimals: 0, after: true }, ARS: { symbol: 'ARS', decimals: 2, after: true },
	PEN: { symbol: 'S/', decimals: 2 }, NGN: { symbol: '₦', decimals: 2 },
	SAR: { symbol: 'SAR', decimals: 2, after: true }, ILS: { symbol: '₪', decimals: 2 },
	AED: { symbol: 'AED', decimals: 2, after: true }, TWD: { symbol: 'NT$', decimals: 2 },
	NOK: { symbol: 'kr', decimals: 2, after: true }, KWD: { symbol: 'KD', decimals: 3 },
	NZD: { symbol: 'NZ$', decimals: 2 }, SGD: { symbol: 'SG$', decimals: 2 },
	MYR: { symbol: 'RM', decimals: 2 }, ISK: { symbol: 'kr', decimals: 0, after: true },
	// Social-casino currencies — letter codes, always after, never "$"
	XGC: { symbol: 'GC', decimals: 2, after: true },
	XSC: { symbol: 'SC', decimals: 2, after: true },
	XEC: { symbol: 'SC', decimals: 2, after: true },
};

// Active display currency: the RGS balance currency wins once known; else the launch param.
let activeCurrency = session.currency;
export function setCurrency(code: string) { if (code) activeCurrency = code.toUpperCase(); }
export function currencyCode(): string { return activeCurrency; }

/** Format an RGS micro-amount (1_000_000 = 1.00) for the active currency.
 * Shows extra precision for sub-cent values so a 0.1x win on a $0.01 bet never reads 0.00. */
export function fmtMoney(micro: number): string {
	const meta: Meta = CURRENCY[activeCurrency] ?? { symbol: activeCurrency, decimals: 2, after: true };
	const value = micro / 1_000_000;
	let decimals = meta.decimals;
	// sub-unit precision: if the value is non-zero but would round away, widen decimals (max 6)
	if (value !== 0) {
		while (decimals < 6 && Math.abs(value) < 1 / 10 ** decimals / 2) decimals++;
		if (decimals === meta.decimals && Math.abs(value) > 0 && Number(value.toFixed(decimals)) === 0) {
			decimals = Math.min(6, decimals + 2);
		}
	}
	const n = value.toFixed(decimals);
	return meta.after ? `${n} ${meta.symbol}` : `${meta.symbol}${n}`;
}
