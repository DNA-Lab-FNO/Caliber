import { svelte } from '@sveltejs/vite-plugin-svelte'
import autoprefixer from 'autoprefixer'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const production = mode === 'production'

  return {
    define: {
      __API_BASE__: JSON.stringify(
	    production ? '/caliber/api' : '/api'
	  ),
   	},
    plugins: [svelte({ emitCss: true })],
    base: production ? '/caliber/static/svelte/' : '/',
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': 'http://localhost:8000',
      },
    },
    build: {
      outDir: '../static/svelte',
      emptyOutDir: true,
      rollupOptions: {
        output: {
          entryFileNames: 'main.js',
          assetFileNames: (assetInfo) => {
            if (assetInfo.name && assetInfo.name.endsWith('.css')) {
              return 'main.css'
            }
            return 'assets/[name][extname]'
          },
        },
      },
    },
    css: {
      postcss: {
        plugins: [autoprefixer()],
      },
    },
  }
})
