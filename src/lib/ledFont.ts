// Stock-broker LED bitmap fonts. Green & red share one layout (544x276); white is a
// full glyph sheet (816x460). All rows are 77px tall so glyphs share a baseline.
export interface Glyph { x: number; y: number; w: number; h: number }
export interface LedFont { src: string; aw: number; ah: number; rowH: number; glyphs: Record<string, Glyph> }

// green/red: 0-9 $ . , + - % (two 77px rows)
const NUM_GLYPHS: Record<string, Glyph> = {
	'0': { x: 6, y: 4, w: 57, h: 77 },
	'1': { x: 85, y: 4, w: 35, h: 77 },
	'2': { x: 142, y: 4, w: 57, h: 77 },
	'3': { x: 211, y: 4, w: 56, h: 77 },
	'4': { x: 278, y: 4, w: 56, h: 77 },
	'5': { x: 346, y: 4, w: 57, h: 77 },
	'6': { x: 414, y: 4, w: 57, h: 77 },
	'7': { x: 483, y: 4, w: 56, h: 77 },
	'8': { x: 6, y: 96, w: 57, h: 77 },
	'9': { x: 74, y: 96, w: 57, h: 77 },
	'$': { x: 143, y: 96, w: 55, h: 77 },
	'.': { x: 220, y: 96, w: 27, h: 77 },
	',': { x: 289, y: 96, w: 26, h: 77 },
	'+': { x: 347, y: 96, w: 55, h: 77 },
	'-': { x: 415, y: 96, w: 55, h: 77 },
	'%': { x: 482, y: 96, w: 57, h: 77 },
};

// white: full A-Z 0-9 + symbols; mapping the glyphs we render (digits, $ . , and WIN)
const WHITE_GLYPHS: Record<string, Glyph> = {
	'0': { x: 142, y: 188, w: 57, h: 77 },
	'1': { x: 221, y: 188, w: 35, h: 77 },
	'2': { x: 278, y: 188, w: 57, h: 77 },
	'3': { x: 347, y: 188, w: 56, h: 77 },
	'4': { x: 414, y: 188, w: 56, h: 77 },
	'5': { x: 482, y: 188, w: 57, h: 77 },
	'6': { x: 550, y: 188, w: 57, h: 77 },
	'7': { x: 619, y: 188, w: 56, h: 77 },
	'8': { x: 686, y: 188, w: 57, h: 77 },
	'9': { x: 754, y: 188, w: 57, h: 77 },
	'$': { x: 7, y: 280, w: 55, h: 77 },
	'.': { x: 356, y: 280, w: 27, h: 77 },
	',': { x: 493, y: 280, w: 26, h: 77 },
	'W': { x: 686, y: 96, w: 57, h: 77 },
	'I': { x: 551, y: 4, w: 55, h: 77 },
	'N': { x: 74, y: 96, w: 57, h: 77 },
};

export const LED_FONTS: Record<'green' | 'red' | 'white', LedFont> = {
	green: { src: '/led_green.png', aw: 544, ah: 276, rowH: 77, glyphs: NUM_GLYPHS },
	red: { src: '/led_red.png', aw: 544, ah: 276, rowH: 77, glyphs: NUM_GLYPHS },
	white: { src: '/led_white.png', aw: 816, ah: 460, rowH: 77, glyphs: WHITE_GLYPHS },
};
