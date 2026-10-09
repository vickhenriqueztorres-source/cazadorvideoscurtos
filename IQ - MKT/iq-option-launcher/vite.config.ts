import { cp, mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { build as esbuild } from 'esbuild';
import { defineConfig, type Plugin } from 'vite';
import manifest from './manifest.config';

const projectRoot = resolve(import.meta.dirname);
const dist = resolve(projectRoot, 'dist');

function extensionBundle(): Plugin {
  return {
    name: 'extension-bundle',
    async closeBundle() {
      await mkdir(resolve(dist, 'content'), { recursive: true });
      await mkdir(resolve(dist, 'background'), { recursive: true });
      await Promise.all([
        esbuild({
          entryPoints: [resolve(projectRoot, 'src/content/bootstrap.ts')],
          outfile: resolve(dist, 'content/bootstrap.js'),
          bundle: true,
          format: 'iife',
          target: 'chrome120',
          minify: false,
          sourcemap: true
        }),
        esbuild({
          entryPoints: [resolve(projectRoot, 'src/background/service-worker.ts')],
          outfile: resolve(dist, 'background/service-worker.js'),
          bundle: true,
          format: 'esm',
          target: 'chrome120',
          minify: false,
          sourcemap: true
        })
      ]);
      await cp(resolve(projectRoot, 'config'), resolve(dist, 'config'), { recursive: true });
      await writeFile(resolve(dist, 'manifest.json'), JSON.stringify(manifest, null, 2));
    }
  };
}

export default defineConfig({
  root: resolve(projectRoot, 'src'),
  base: './',
  plugins: [extensionBundle()],
  build: {
    outDir: dist,
    emptyOutDir: true,
    target: 'chrome120',
    rollupOptions: {
      input: {
        'popup/popup': resolve(projectRoot, 'src/popup/popup.html'),
        'options/options': resolve(projectRoot, 'src/options/options.html')
      }
    }
  }
});
