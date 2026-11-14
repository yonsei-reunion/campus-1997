// 새 소식 entries (data/releases.json) as DOM, shared by the in-game panel (news.js) and the news page (news.html).
// No imports: the news page loads only this file, not the game.

// items: string | { text, items: [...] } (sublists nest to any depth)
export function renderItems(items) {
  const ul = document.createElement('ul');
  for (const it of items) {
    const li = document.createElement('li');
    if (typeof it === 'string') li.textContent = it;
    else { li.append(it.text || ''); if (it.items?.length) li.appendChild(renderItems(it.items)); }
    ul.appendChild(li);
  }
  return ul;
}

// 2026-11-06 → 2026년 11월 6일
export function dateLabel(date) {
  const [y, m, d] = date.split('-').map(Number);
  return `${y}년 ${m}월 ${d}일`;
}

// one dated entry: { date, summary, groups: [{ category, items, images: [{ src, alt }] }] } →
// <section id="2026-11-06"><h3>2026년 11월 6일</h3><p class="summary">…</p><div class="cat"><h4>건물</h4><ul>…</ul><figure class="shot">…</div>…
// heading: the date's tag (each category gets the next level); link: the date's URL (none: plain text); src: maps each capture's URL
export function noteSection(n, { heading = 'h3', link = '', src = (u) => u } = {}) {
  const sec = document.createElement('section');
  sec.id = n.date;
  const h = document.createElement(heading);
  const date = link ? h.appendChild(Object.assign(document.createElement('a'), { href: link })) : h;
  date.textContent = dateLabel(n.date);
  sec.appendChild(h);
  if (n.summary) sec.appendChild(Object.assign(document.createElement('p'), { className: 'summary', textContent: n.summary }));
  const sub = 'h' + (Number(heading[1]) + 1);
  for (const g of n.groups) {
    const cat = document.createElement('div');
    cat.className = 'cat';
    cat.append(Object.assign(document.createElement(sub), { textContent: g.category }), renderItems(g.items));
    for (const im of g.images || []) {
      const fig = document.createElement('figure');
      fig.className = 'shot';
      const img = document.createElement('img');
      img.src = src(im.src); img.alt = im.alt || ''; img.loading = 'lazy';
      const cap = document.createElement('figcaption');
      cap.textContent = im.alt || '';
      fig.append(img, cap);
      cat.appendChild(fig);
    }
    sec.appendChild(cat);
  }
  return sec;
}
