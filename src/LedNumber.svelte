<script lang="ts">
	import { LED_FONTS } from './lib/ledFont';

	let { text, color = 'white', height = 24 }: {
		text: string;
		color?: 'green' | 'red' | 'white';
		height?: number;
	} = $props();

	const font = $derived(LED_FONTS[color]);
	const scale = $derived(height / font.rowH);
	const chars = $derived([...text]);
</script>

<span class="led" style="height:{height}px; gap:{Math.max(1, height * 0.06)}px">
	{#each chars as ch, i (i)}
		{#if font.glyphs[ch]}
			{@const g = font.glyphs[ch]}
			<span
				class="g"
				style="
					width:{g.w * scale}px;
					height:{g.h * scale}px;
					background-image:url({font.src});
					background-position:{-g.x * scale}px {-g.y * scale}px;
					background-size:{font.aw * scale}px {font.ah * scale}px;
				"
			></span>
		{:else}
			<span class="sp" style="width:{height * 0.3}px; height:{height}px"></span>
		{/if}
	{/each}
</span>

<style>
	.led { display: inline-flex; align-items: center; vertical-align: middle; }
	.g { display: inline-block; background-repeat: no-repeat; flex: none; }
	.sp { display: inline-block; flex: none; }
</style>
