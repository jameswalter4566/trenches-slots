<script lang="ts">
	import { onMount } from 'svelte';
	import { SlotBoard } from './lib/board';
	import { displayGrid, godCandlePeak, spin, type SpinResult } from './lib/sim';
	import { fmtMoney } from './lib/session';
	import { sfx } from './lib/sound';
	import { BONUS_BUY_COST, FREE_SPINS_AWARD, FS_RETRIGGER_SPINS } from './lib/paytable';

	const BET_LEVELS = [200000, 400000, 600000, 1_000000, 2_000000, 4_000000, 10_000000, 20_000000, 50_000000, 100_000000];
	const params = new URLSearchParams(location.search);
	// dev art preview: ?testwin=rocket guarantees that symbol wins every spin
	const TEST_WIN = (params.get('testwin') ?? undefined) as
		import('./lib/paytable').PayingSymbol | undefined;
	// dev: ?testjackpot forces the GOD CANDLE jackpot; ?jackpotx=250 forces its peak
	const TEST_JACKPOT = params.has('testjackpot') || params.has('jackpotx');
	const JACKPOT_X = params.has('jackpotx') ? Number(params.get('jackpotx')) : 0;
	const nextPeak = () => (JACKPOT_X > 0 ? JACKPOT_X : godCandlePeak());

	let boardEl: HTMLDivElement;
	let board: SlotBoard | null = null;

	let balance = $state(1000_000000);
	let betIndex = $state(3); // $1.00
	let spinning = $state(false);
	let lastWin = $state(0);
	let muted = $state(false);

	let fsActive = $state(false);
	let fsLeft = $state(0);
	let fsTotalMult = $state(0);
	let fsTotalWin = $state(0);
	let fsIntro = $state(false);
	let fsSummary = $state(false);

	const bet = $derived(BET_LEVELS[betIndex]);
	const bonusCost = $derived(bet * BONUS_BUY_COST);
	const canSpin = $derived(!spinning && !fsActive && balance >= bet);
	const canBuy = $derived(!spinning && !fsActive && balance >= bonusCost);

	onMount(async () => {
		await document.fonts.load('700 20px DynaPuff');
		board = new SlotBoard();
		await board.init(boardEl);
		await board.primeIdle(displayGrid());
		const onKey = (e: KeyboardEvent) => {
			if (e.code === 'Space') {
				e.preventDefault();
				void doSpin();
			}
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});

	async function doSpin() {
		if (!board || !canSpin) return;
		sfx.unlock();
		spinning = true;
		lastWin = 0;
		balance -= bet;
		if (TEST_JACKPOT) {
			const win = await board.godCandleJackpot(bet, nextPeak());
			balance += win;
			lastWin = win;
			await board.primeIdle(displayGrid());
			spinning = false;
			return;
		}
		const result = spin(bet, { forceWin: TEST_WIN });
		await board.replaySpin(result);
		balance += result.totalWinMicro;   // paying win + money gun + mystery candle prizes
		lastWin = result.totalWinMicro;
		// a MYSTERY candle hit the jackpot → the full price-action run (separate payout)
		if (result.mysteryJackpot) {
			const win = await board.godCandleJackpot(bet, nextPeak());
			balance += win;
			lastWin = win;
			await board.primeIdle(displayGrid());
		} else if (result.triggersFreeSpins) {
			await runFreeSpins();
		}
		spinning = false;
	}

	async function buyBonus() {
		if (!board || !canBuy) return;
		sfx.unlock();
		spinning = true;
		lastWin = 0;
		balance -= bonusCost;
		const result = spin(bet, { forceBonus: true });
		await board.replaySpin(result);
		balance += result.totalWinMicro;
		lastWin = result.totalWinMicro;
		await runFreeSpins();
		spinning = false;
	}

	async function runFreeSpins() {
		if (!board) return;
		fsActive = true;
		fsLeft = FREE_SPINS_AWARD;
		fsTotalMult = 0;
		fsTotalWin = 0;
		fsIntro = true;
		sfx.fsTrigger();
		await new Promise((r) => setTimeout(r, 1900));
		fsIntro = false;

		while (fsLeft > 0) {
			fsLeft -= 1;
			const result: SpinResult = spin(bet, { freeSpin: true, fsTotalMult });
			await board.replaySpin(result);
			if (result.appliedMult > 0) {
				fsTotalMult = result.appliedMult; // sim returns the NEW running total
				board.setMultBadge(fsTotalMult);
			}
			if (result.retrigger) fsLeft += FS_RETRIGGER_SPINS;
			balance += result.totalWinMicro;
			fsTotalWin += result.totalWinMicro;
			lastWin = result.totalWinMicro;
			await new Promise((r) => setTimeout(r, 260));
		}

		board.setMultBadge(null);
		fsSummary = true;
		sfx.bigWin();
	}

	function closeSummary() {
		fsSummary = false;
		fsActive = false;
	}

	function stepBet(dir: number) {
		if (spinning || fsActive) return;
		betIndex = Math.max(0, Math.min(BET_LEVELS.length - 1, betIndex + dir));
	}

	function toggleMute() {
		muted = !muted;
		sfx.setMuted(muted);
	}
</script>

<div class="shell">
	<header>
		<div class="logo">
			<span class="logo-main">GOD CANDLE</span>
			<span class="logo-sub">TRENCHES SLOTS · PROTOTYPE</span>
		</div>
		{#if fsActive && !fsIntro && !fsSummary}
			<div class="fs-hud">
				<span class="fs-count">{fsLeft}</span> FREE SPINS
				{#if fsTotalMult > 0}<span class="fs-mult">x{fsTotalMult}</span>{/if}
			</div>
		{/if}
		<button class="mute" onclick={toggleMute} aria-label="toggle sound">{muted ? 'SOUND OFF' : 'SOUND ON'}</button>
	</header>

	<div class="board" bind:this={boardEl}></div>

	<!-- FLOOR TRADER mascot: transparent idle loop beside the arcade screen -->
	<video
		class="mascot"
		autoplay
		loop
		muted
		playsinline
		poster="/mascot/floor_trader_poster.png"
		aria-hidden="true"
	>
		<source src="/mascot/floor_trader.webm" type="video/webm" />
	</video>

	<footer>
		<div class="readout">
			<span class="readout-label">BALANCE</span>
			<span class="readout-value">{fmtMoney(balance)}</span>
		</div>

		<div class="bet">
			<button class="bet-step" onclick={() => stepBet(-1)} disabled={spinning || fsActive || betIndex === 0}>−</button>
			<div class="readout bet-readout">
				<span class="readout-label">BET</span>
				<span class="readout-value">{fmtMoney(bet)}</span>
			</div>
			<button class="bet-step" onclick={() => stepBet(1)} disabled={spinning || fsActive || betIndex === BET_LEVELS.length - 1}>+</button>
		</div>

		<button class="buy" onclick={buyBonus} disabled={!canBuy}>
			BUY BONUS
			<span class="buy-cost">{fmtMoney(bonusCost)}</span>
		</button>

		<button class="spin" onclick={doSpin} disabled={!canSpin}>
			{spinning ? '...' : 'SPIN'}
		</button>

		<div class="readout">
			<span class="readout-label">WIN</span>
			<span class=”readout-value win-value”>{lastWin > 0 ? fmtMoney(lastWin) : '—'}</span>
		</div>
	</footer>

	{#if fsIntro}
		<div class="overlay">
			<div class="overlay-card">
				<div class="overlay-title">{FREE_SPINS_AWARD} FREE SPINS</div>
				<div class="overlay-sub">orbs stack the multiplier for the whole bonus</div>
			</div>
		</div>
	{/if}

	{#if fsSummary}
		<div class="overlay" onclick={closeSummary} onkeydown={closeSummary} role="button" tabindex="0">
			<div class="overlay-card">
				<div class="overlay-title gold">BONUS PAID</div>
				<div class="overlay-amount">{fmtMoney(fsTotalWin)}</div>
				<div class="overlay-sub">tap to continue</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.shell {
		height: 100%;
		display: flex;
		flex-direction: column;
		position: relative;
	}
	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 14px 22px 6px;
	}
	.logo { display: flex; flex-direction: column; line-height: 1; }
	.logo-main {
		font-family: 'DynaPuff';
		font-weight: 700;
		font-size: 30px;
		color: #2be26a;
		letter-spacing: 0.5px;
	}
	.logo-sub {
		font-family: 'IBM Plex Mono';
		font-size: 11px;
		color: #7a8294;
		margin-top: 4px;
		letter-spacing: 2px;
	}
	.fs-hud {
		font-family: 'DynaPuff';
		font-weight: 700;
		font-size: 20px;
		color: #fff;
		background: #123b23;
		border: 2px solid #2be26a;
		border-radius: 14px;
		padding: 8px 18px;
	}
	.fs-count { color: #2be26a; font-size: 24px; }
	.fs-mult { color: #f7c843; margin-left: 12px; }
	.mute {
		font-family: 'IBM Plex Mono';
		font-size: 11px;
		letter-spacing: 1px;
		color: #7a8294;
		background: #171a22;
		border: 2px solid #262b38;
		border-radius: 10px;
		padding: 8px 12px;
		cursor: pointer;
	}
	.board { flex: 1; min-height: 0; }
	/* FLOOR TRADER mascot — stands tall in the right gutter beside the centered board,
	   flipped to face the screen */
	.mascot {
		position: absolute;
		right: clamp(0px, 1vw, 40px);
		bottom: 170px;
		width: clamp(300px, 34vw, 560px);
		height: auto;
		transform: scaleX(-1);
		pointer-events: none;
		user-select: none;
		z-index: 2;
		filter: drop-shadow(0 18px 28px rgba(0, 0, 0, 0.55));
	}
	/* on narrow screens the board fills the width — hide the mascot so it never overlaps */
	@media (max-width: 1024px) {
		.mascot { display: none; }
	}
	footer {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 18px;
		padding: 10px 22px 20px;
	}
	.readout {
		display: flex;
		flex-direction: column;
		align-items: center;
		background: #171a22;
		border: 2px solid #262b38;
		border-radius: 14px;
		padding: 8px 18px;
		min-width: 130px;
	}
	.readout-label {
		font-family: 'IBM Plex Mono';
		font-size: 10px;
		letter-spacing: 2px;
		color: #7a8294;
	}
	.readout-value {
		font-family: 'DynaPuff';
		font-weight: 700;
		font-size: 20px;
		color: #fff;
	}
	.win-value { color: #2be26a; }
	.bet { display: flex; align-items: center; gap: 8px; }
	.bet-readout { min-width: 110px; }
	.bet-step {
		font-family: 'DynaPuff';
		font-weight: 700;
		font-size: 24px;
		width: 46px;
		height: 46px;
		border-radius: 12px;
		border: none;
		cursor: pointer;
		color: #fff;
		background: #262b38;
		box-shadow: 0 5px 0 #14161d;
	}
	.bet-step:active:not(:disabled) { transform: translateY(4px); box-shadow: 0 1px 0 #14161d; }
	.bet-step:disabled { opacity: 0.35; cursor: default; }
	.spin {
		font-family: 'DynaPuff';
		font-weight: 700;
		font-size: 30px;
		color: #06250f;
		background: #2be26a;
		border: none;
		border-radius: 18px;
		padding: 16px 54px;
		cursor: pointer;
		box-shadow: 0 8px 0 #0f7a38;
	}
	.spin:active:not(:disabled) { transform: translateY(6px); box-shadow: 0 2px 0 #0f7a38; }
	.spin:disabled { opacity: 0.45; cursor: default; }
	.buy {
		font-family: 'DynaPuff';
		font-weight: 700;
		font-size: 16px;
		color: #3a2a00;
		background: #f7c843;
		border: none;
		border-radius: 14px;
		padding: 10px 20px;
		cursor: pointer;
		box-shadow: 0 6px 0 #b8860b;
		display: flex;
		flex-direction: column;
		align-items: center;
	}
	.buy-cost { font-family: 'IBM Plex Mono'; font-size: 11px; font-weight: 600; }
	.buy:active:not(:disabled) { transform: translateY(5px); box-shadow: 0 1px 0 #b8860b; }
	.buy:disabled { opacity: 0.45; cursor: default; }
	.overlay {
		position: absolute;
		inset: 0;
		background: rgba(5, 6, 9, 0.82);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 10;
	}
	.overlay-card {
		background: #171a22;
		border: 3px solid #2be26a;
		border-radius: 24px;
		box-shadow: 0 10px 0 rgba(0, 0, 0, 0.5);
		padding: 44px 64px;
		text-align: center;
	}
	.overlay-title {
		font-family: 'DynaPuff';
		font-weight: 700;
		font-size: 46px;
		color: #2be26a;
	}
	.overlay-title.gold { color: #f7c843; }
	.overlay-amount {
		font-family: 'DynaPuff';
		font-weight: 700;
		font-size: 58px;
		color: #fff;
		margin-top: 10px;
	}
	.overlay-sub {
		font-family: 'IBM Plex Mono';
		font-size: 13px;
		color: #7a8294;
		margin-top: 14px;
		letter-spacing: 1px;
	}
</style>
