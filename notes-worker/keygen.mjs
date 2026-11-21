// 전체 순위의 키(P-256 ECDH)를 새로 만든다. 출력한 JWK 한 줄을 secret 으로:
//   node keygen.mjs | npx wrangler secret put RANK_KEY
// 로컬 시험은 .dev.vars 에 RANK_KEY='<JWK>' 한 줄(커밋하지 않음). 키를 바꾸면 그 전에 받은 판 열쇠 · 영수증은 모두 무효.
const k = await crypto.subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
process.stdout.write(JSON.stringify(await crypto.subtle.exportKey('jwk', k.privateKey)));
