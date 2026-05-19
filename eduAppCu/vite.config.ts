import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

/**
 * Плагин для корректного разрешения ассетов из Figma.
 * Заменяет префикс figma:asset/ на абсолютный путь к папке src/assets.
 */
function figmaAssetResolver() {
  return {
    name: 'figma-asset-resolver',
    resolveId(id: string) {
      if (id.startsWith('figma:asset/')) {
        const filename = id.replace('figma:asset/', '')
        return path.resolve(__dirname, 'src/assets', filename)
      }
    },
  }
}

export default defineConfig({
  // Кэш вынесен из node_modules, чтобы избежать проблем с правами доступа
  cacheDir: path.resolve(__dirname, '.vite-cache'),

  plugins: [
    figmaAssetResolver(),
    react(),
    tailwindcss(),
  ],

  resolve: {
    alias: {
      // Псевдоним @ для быстрого доступа к исходникам из любой папки
      '@': path.resolve(__dirname, './src'),
    },
  },

  server: {
    // 0.0.0.0 открывает доступ к серверу из внешней сети
    host: '0.0.0.0',

    // Порт, который открыт на вашем сервере
    port: 8080,
        // Если 8080 занят, Vite не будет пытаться занять другой порт
    strictPort: true,

    // Белый список хостов для защиты от атак через заголовок Host
    allowedHosts: [
      'yasnenko.ru',
      '.yasnenko.ru'
    ],

    // Проксирование запросов к бэкенду (Flask)
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
        secure: false,
      },
    },

    // Настройка Hot Module Replacement (живая перезагрузка) для работы через домен
    hmr: {
      host: 'yasnenko.ru',
      clientPort: 8080
    }
  },

  // Указываем, какие типы файлов можно импортировать напрямую
  assetsInclude: ['**/*.svg', '**/*.csv'],
})