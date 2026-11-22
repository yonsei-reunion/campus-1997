// 메타모아(https://metamoa.com) 공간 페이지의 「N명 접속 중」. GA4 실시간 보고서에서 최근 5분 동안의 활성 사용자를 읽어
// 그대로 보낸다(0명이면 0). 게임은 화면을 보는 동안 1분마다 heartbeat 이벤트를 보내므로(web/src/ga.js), 오래 걷는
// 사람도 이 5분 안에 든다. 광고 차단 · 추적 방지를 켠 사람은 GA 에 잡히지 않아 실제보다 적게 나올 수 있다.
//
// 언제: wrangler.jsonc 의 cron. 1시간에 한 번, 한국 시각 01:00 ~ 04:00 은 건너뛴다.
// secret: GA_SA (GA 속성의 「뷰어」인 서비스 계정의 JSON 키 통째로), METAMOA_KEY (공간 키 mm_live_)
// vars:   GA_PROPERTY (GA4 속성 번호), METAMOA_SPACE (공간 id)

const enc = new TextEncoder();
const b64u = (bytes) => btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const b64uJSON = (o) => b64u(enc.encode(JSON.stringify(o)));

// 서비스 계정 키로 서명한 JWT 를 접근 토큰으로 바꾼다(한 시간짜리지만 한 번 쓰고 버림)
async function googleToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  const body = `${b64uJSON({ alg: 'RS256', typ: 'JWT' })}.${b64uJSON({
    iss: sa.client_email,
    scope: 'https://www.googleapis.com/auth/analytics.readonly',
    aud: 'https://oauth2.googleapis.com/token',
    iat: now,
    exp: now + 3600,
  })}`;
  const der = Uint8Array.from(atob(sa.private_key.replace(/-----[^-]+-----|\s/g, '')), (c) => c.charCodeAt(0));
  const key = await crypto.subtle.importKey('pkcs8', der, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', key, enc.encode(body));
  const res = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer', assertion: `${body}.${b64u(sig)}` }),
  });
  const out = await res.json().catch(() => ({}));
  if (!res.ok || !out.access_token) throw new Error(`Google 토큰 ${res.status}: ${JSON.stringify(out).slice(0, 160)}`);
  return out.access_token;
}

export async function activeUsers(env) {
  if (!env.GA_SA) throw new Error('GA_SA 가 없어요');
  const token = await googleToken(JSON.parse(env.GA_SA));
  const res = await fetch(`https://analyticsdata.googleapis.com/v1beta/properties/${env.GA_PROPERTY}:runRealtimeReport`, {
    method: 'POST',
    headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
    body: JSON.stringify({ metrics: [{ name: 'activeUsers' }], minuteRanges: [{ startMinutesAgo: 4, endMinutesAgo: 0 }] }),
  });
  const out = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`GA 실시간 ${res.status}: ${JSON.stringify(out).slice(0, 160)}`);
  return Number(out.rows?.[0]?.metricValues?.[0]?.value ?? 0);   // 아무도 없으면 rows 가 없다
}

export async function push(env) {
  if (!env.METAMOA_KEY) throw new Error('METAMOA_KEY 가 없어요');
  const count = await activeUsers(env);
  const res = await fetch(`https://metamoa.com/api/live/${env.METAMOA_SPACE}`, {
    method: 'POST',
    headers: { authorization: `Bearer ${env.METAMOA_KEY}`, 'content-type': 'application/json', 'user-agent': 'y97-notes-worker' },
    body: JSON.stringify({ count }),
  });
  // 204 받음 · 429 9분 안에 다시(손으로 연달아 돌렸을 때): 둘 다 그냥 넘어간다
  if (res.status !== 204 && res.status !== 429) throw new Error(`메타모아 ${res.status}: ${(await res.text()).slice(0, 160)}`);
  console.log(`live: ${count} → 메타모아 ${res.status}`);
  return { count, status: res.status };
}
