// RTP / house-edge measurement harness. Plays many base spins through the real
// sim (base game + tumbles + orbs + money gun + mystery candles + free spins +
// mystery jackpot) and reports the return-to-player and hit metrics.
//
//   npx tsx tools/rtp.ts [spins]
//
// Target (Stake Engine): RTP in [96.0%, 96.7%] — a ~3.3-4.0% house edge.
import { spin, godCandlePeak } from '../src/lib/sim';
import { FREE_SPINS_AWARD, FS_RETRIGGER_SPINS } from '../src/lib/paytable';

const BET = 1_000_000;
const N = Number(process.argv[2] ?? 500_000);

function simFreeSpins(bet: number): number {
	let total = 0, left = FREE_SPINS_AWARD, fsMult = 0, guard = 0;
	while (left > 0 && guard++ < 500) {
		left--;
		const r = spin(bet, { freeSpin: true, fsTotalMult: fsMult });
		if (r.appliedMult > 0) fsMult = r.appliedMult;
		if (r.retrigger) left += FS_RETRIGGER_SPINS;
		total += r.totalWinMicro;
	}
	return total;
}

let wagered = 0, returned = 0, hits = 0, maxWin = 0;
let baseRet = 0, fsRet = 0, jpRet = 0, gunRet = 0, candleRet = 0, vaultRet = 0, payRet = 0;
let fsHits = 0, jpHits = 0, gunHits = 0, candleHits = 0, bearHits = 0, payHits = 0, vaultHits = 0;

for (let i = 0; i < N; i++) {
	wagered += BET;
	const r = spin(BET, {});
	let win = r.totalWinMicro;
	baseRet += r.totalWinMicro;
	gunRet += r.moneygunWinMicro; if (r.moneygunWinMicro > 0) gunHits++;
	candleRet += r.candlePrizeMicro; if (r.candleReveal.length > 0) candleHits++;
	vaultRet += r.vaultWinMicro; if (r.vaultWinMicro > 0) vaultHits++;
	// net line+scatter pay after the bear penalty (what the tumble actually pays)
	const pay = r.totalWinMicro - r.moneygunWinMicro - r.vaultWinMicro - r.candlePrizeMicro;
	payRet += pay; if (pay > 0) payHits++;
	if (r.bearCount > 0 && r.grossWinMicro > 0) bearHits++;
	if (r.mysteryJackpot) {
		const jp = Math.round(BET * godCandlePeak());
		win += jp; jpRet += jp; jpHits++;
	} else if (r.triggersFreeSpins) {
		const fs = simFreeSpins(BET);
		win += fs; fsRet += fs; fsHits++;
	}
	returned += win;
	if (win > 0) hits++;
	maxWin = Math.max(maxWin, win);
}

const pct = (x: number) => (x / wagered * 100).toFixed(2) + '%';
console.log(`\n  spins        ${N.toLocaleString()}`);
console.log(`  RTP          ${pct(returned)}`);
console.log(`  hit rate     ${(hits / N * 100).toFixed(1)}%`);
console.log(`  max win      ${(maxWin / BET).toFixed(0)}x\n`);
console.log(`  contribution by feature (of total wagered):`);
console.log(`    base spin      ${pct(baseRet)}   (pay+gun+candle+vault, hit ${(hits / N * 100).toFixed(1)}%)`);
console.log(`    LINE PAY       ${pct(payRet)}   (${(payHits / N * 100).toFixed(1)}% of spins)  <- bull/rocket/goldbar/etc`);
console.log(`    money gun      ${pct(gunRet)}   (${(gunHits / N * 100).toFixed(1)}% of spins)`);
console.log(`    vault          ${pct(vaultRet)}   (${(vaultHits / N * 100).toFixed(2)}% of spins)`);
console.log(`    mystery candle ${pct(candleRet)}   (${(candleHits / N * 100).toFixed(1)}% of spins)`);
console.log(`    free spins     ${pct(fsRet)}   (${(fsHits / N * 100).toFixed(2)}% of spins)`);
console.log(`    jackpot        ${pct(jpRet)}   (${(jpHits / N * 100).toFixed(3)}% of spins)`);
console.log(`    bears dumped   ${(bearHits / N * 100).toFixed(1)}% of spins\n`);
