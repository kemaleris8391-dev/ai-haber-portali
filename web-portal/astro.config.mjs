// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

const siteUrl = process.env.SITE_URL || 'https://aihaberler.web.app';

// https://astro.build/config
export default defineConfig({
  site: siteUrl,
  integrations: [sitemap()],
});
