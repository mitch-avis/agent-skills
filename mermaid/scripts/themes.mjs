#!/usr/bin/env node

import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const skillRoot = __dirname;

async function loadBeautifulMermaid() {
  try {
    return await import('beautiful-mermaid');
  } catch {
    console.error('[beautiful-mermaid] Dependency not installed. Install the pinned version with:');
    console.error(`  cd ${skillRoot} && npm ci --ignore-scripts`);
    process.exit(1);
  }
}

async function main() {
  const { THEMES } = await loadBeautifulMermaid();
  const themes = Object.keys(THEMES);

  console.log('Available Beautiful-Mermaid Themes:\n');
  themes.forEach((theme, i) => {
    console.log(`${String(i + 1).padStart(2)}. ${theme}`);
  });

  console.log(`\nTotal: ${themes.length} themes`);
  console.log('\nUsage:');
  console.log('  node scripts/render.mjs --input diagram.mmd --theme <theme-name> --output output.svg');
}

main().catch(e => {
  console.error('Error:', e.message);
  process.exit(1);
});
