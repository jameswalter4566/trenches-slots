import { resolve } from 'node:path';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [svelte()],
	base: './',
	build: {
		rollupOptions: {
			input: {
				main: resolve(__dirname, 'index.html'),
				animTest: resolve(__dirname, 'anim-test.html'),
			},
		},
	},
});
