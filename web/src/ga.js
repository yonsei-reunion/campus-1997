// Google Analytics 4: 방문자 수 · 들어온 곳 · 기기를 본다. 세 쪽(index · news · people)이 <head> 에서 이 파일을 읽는다.
//
// - 측정 ID(G-…)는 아래 GA_ID 한 곳에. 비어 있으면 아무것도 하지 않는다.
// - 배포 주소(yonsei-1997.benelog.net)에서만 센다: 로컬 vite · 캡처 도구(headless, navigator.webdriver)는 빼서
//   개발 중의 열기가 방문으로 쌓이지 않게.
// - 박동: 화면을 보고 있는 동안 1분마다 heartbeat 이벤트를 보낸다. 3D 게임은 한 번 열면 오래 걷는데 GA4 는 쪽을 열 때
//   말고는 이벤트를 보내지 않아, 실시간 보고서의 「지난 N분 활성 사용자」에서 걷는 사람이 빠지기 때문이다(동시 접속자를
//   GA 실시간 API 로 셀 때의 바탕).
const GA_ID = 'G-BT3PCZNR1Z';  // GA4 속성 yonsei-1997.benelog.net (계정 benelog.net)
const HOSTS = ['yonsei-1997.benelog.net'];
const BEAT_MS = 60_000;

const on = GA_ID && HOSTS.includes(location.hostname) && !navigator.webdriver;

window.dataLayer = window.dataLayer || [];
function gtag() { window.dataLayer.push(arguments); }

if (on) {
  const s = document.createElement('script');
  s.async = true;
  s.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
  document.head.appendChild(s);
  gtag('js', new Date());
  gtag('config', GA_ID);
  setInterval(() => { if (document.visibilityState === 'visible') gtag('event', 'heartbeat'); }, BEAT_MS);
}

// 게임 쪽에서 이벤트를 남길 때: track('shoot_end', { score: 12 }). 꺼져 있으면 아무것도 하지 않음
export function track(name, params) {
  if (on) gtag('event', name, params);
}
