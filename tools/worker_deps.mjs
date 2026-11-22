// Worker(notes-worker, y97-notes)를 이루는 파일: wrangler.jsonc 와 src/index.js 가 (건너건너) 불러오는 모든 파일.
// 이 가운데 하나라도 바뀌면 Worker 를 다시 배포해야 한다(tools/deploy_worker.sh, .github/workflows/worker.yml).
//   node tools/worker_deps.mjs            목록을 저장소 기준 경로로 한 줄씩
//   node tools/worker_deps.mjs --match    표준 입력의 경로(한 줄씩) 가운데 목록에 든 것만 적음
// import 를 글로 읽어 따라간다(상대 경로만: Worker 는 npm 패키지를 쓰지 않는다). 못 찾는 파일이 있으면 실패한다.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const rel = (p) => path.relative(root, p).split(path.sep).join('/');
const CONFIG = path.join(root, 'notes-worker/wrangler.jsonc');
const ENTRY = path.join(root, 'notes-worker/src/index.js');
const SPEC = /(?:\bimport\s*(?:[^'"()]*?\bfrom\s*)?|\bexport\s[^'"]*?\bfrom\s*|\bimport\s*\(\s*)(['"])([^'"]+)\1/g;

export function workerFiles() {
  const seen = new Set([CONFIG]), todo = [ENTRY], bare = new Set();
  while (todo.length) {
    const f = todo.pop();
    if (seen.has(f)) continue;
    if (!fs.existsSync(f)) throw new Error(`Worker 가 불러오는 파일이 없음: ${rel(f)}`);
    seen.add(f);
    if (!/\.(m?js)$/.test(f)) continue;                 // (json 등은 끝)
    const src = fs.readFileSync(f, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
    for (const m of src.matchAll(SPEC)) {
      if (m[2].startsWith('.')) todo.push(path.resolve(path.dirname(f), m[2]));
      else bare.add(m[2]);
    }
  }
  return { files: [...seen].map(rel).sort(), bare: [...bare].sort() };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const { files, bare } = workerFiles();
  if (bare.length) console.error('상대 경로가 아닌 import(따라가지 않음): ' + bare.join(', '));
  if (process.argv.includes('--match')) {
    const want = new Set(files);
    const given = fs.readFileSync(0, 'utf8').split('\n').map((s) => s.trim()).filter(Boolean);
    for (const g of given) if (want.has(g)) console.log(g);
  } else console.log(files.join('\n'));
}
