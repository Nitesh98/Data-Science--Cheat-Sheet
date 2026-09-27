// Builds dist/khetsaathi-demo.html: the whole app (HTML + CSS + core + UI) in one file.
// It runs with no server (demo mode, data kept in the browser), so it can be hosted
// anywhere static: GitHub Pages, Netlify drop, or opened straight from disk.
'use strict';
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const read = (f) => fs.readFileSync(path.join(root, 'public', f), 'utf8');
let html = read('index.html');
const inlineScript = (src) => `<script>\n${src.replace(/<\/script/gi, '<\\/script')}\n</script>`;
html = html
  .replace('<link rel="stylesheet" href="style.css">', () => `<style>\n${read('style.css')}\n</style>`)
  .replace('<link rel="manifest" href="manifest.webmanifest">\n', '')
  .replace('<script src="core.js"></script>', () => inlineScript(read('core.js')))
  .replace('<script src="app.js"></script>', () => inlineScript(read('app.js')));

const out = path.join(root, 'dist', 'khetsaathi-demo.html');
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, html);

// Artifact flavour: same page without the outer document tags (the host adds them).
const body = html.match(/<body>([\s\S]*)<\/body>/)[1];
const head = html.match(/<head>([\s\S]*)<\/head>/)[1].replace(/<meta charset[^>]*>\n|<meta name="viewport"[^>]*>\n/g, '');
fs.writeFileSync(path.join(root, 'dist', 'artifact.html'), head + body);
console.log(`Built ${path.relative(process.cwd(), out)} (${Math.round(html.length / 1024)} KB)`);
