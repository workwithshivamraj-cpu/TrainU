import { mkdir, readdir, copyFile, rm } from 'node:fs/promises';
const source = new URL('../../docs/', import.meta.url);
const target = new URL('../public/docs/', import.meta.url);
const publicDocuments = new Set(['demo-videos.md', 'product.md']);
await mkdir(target, { recursive: true });
for (const name of await readdir(target)) {
  if (name.endsWith('.md') && !publicDocuments.has(name)) await rm(new URL(name, target));
}
for (const name of publicDocuments) {
  await copyFile(new URL(name, source), new URL(name, target));
}
