// news-loader.js
// این اسکریپت محتوای واقعی news/latest.json را جایگزین متن‌های نمونه سایت می‌کند.
// اگر فایل پیدا نشود یا فرمتش خراب باشد، سایت به همان حالت نمونه فعلی باقی می‌ماند.

const CATEGORY_META = {
  siasi:    { tagClass: 'tag-siasi',    label: 'سیاسی',   bg: 'var(--navy-tint)' },
  varzeshi: { tagClass: 'tag-varzeshi', label: 'ورزشی',   bg: 'var(--green-tint)' },
  ejtemaei: { tagClass: 'tag-ejtemaei', label: 'اجتماعی', bg: 'var(--gold-tint)' },
  dakheli:  { tagClass: 'tag-dakheli',  label: 'داخلی',   bg: 'var(--coral-tint)' },
};

const SIDE_ORDER = ['varzeshi', 'ejtemaei', 'dakheli', 'siasi'];

function escapeHTML(str) {
  const d = document.createElement('div');
  d.textContent = str ?? '';
  return d.innerHTML;
}

function relativeTime(isoString) {
  const then = new Date(isoString);
  if (isNaN(then.getTime())) return '';
  const diffMin = Math.floor((Date.now() - then.getTime()) / 60000);
  if (diffMin < 1) return 'همین الان';
  if (diffMin < 60) return `${diffMin} دقیقه پیش`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour} ساعت پیش`;
  const diffDay = Math.floor(diffHour / 24);
  return `${diffDay} روز پیش`;
}

// اگه آیتم عکس واقعی داشته باشه، style مربوط به background-image رو برمی‌گردونه؛
// وگرنه رشته‌ی خالی، تا همون رنگ تینت پیش‌فرض دسته باقی بمونه.
function imageStyle(item, fallbackBg) {
  if (item && item.image_url) {
    return `background-image:url('${item.image_url}');background-size:cover;background-position:center;`;
  }
  return `background:${fallbackBg};`;
}

function creditHTML(item) {
  if (!item || !item.image_url || !item.image_credit) return '';
  const credit = escapeHTML(item.image_credit);
  const href = item.image_credit_url ? escapeHTML(item.image_credit_url) : '#';
  return `<a href="${href}" target="_blank" rel="noopener" style="position:absolute;bottom:6px;left:8px;font-size:10px;color:rgba(255,255,255,0.75);background:rgba(0,0,0,0.35);padding:2px 6px;border-radius:3px;text-decoration:none;">عکس: ${credit}</a>`;
}

function renderHero(item, timeText) {
  const heroBlock = document.querySelector('.hero > div:first-child');
  if (!heroBlock || !item) return;
  const meta = CATEGORY_META[item.category_slug] || {};

  const imgEl = heroBlock.querySelector('.hero-img');
  if (imgEl) {
    imgEl.setAttribute('style', `position:relative;${imageStyle(item, 'linear-gradient(155deg,var(--navy) 0%,#26365c 55%,var(--press-dark) 100%)')}`);
    imgEl.innerHTML = creditHTML(item);
  }

  const tagEl = heroBlock.querySelector('.tag');
  if (tagEl) {
    tagEl.className = `tag ${meta.tagClass || 'tag-siasi'}`;
    tagEl.textContent = item.category_fa || meta.label || '';
  }
  const titleEl = heroBlock.querySelector('.hero-title');
  if (titleEl) titleEl.textContent = item.title || '';
  const excerptEl = heroBlock.querySelector('.hero-excerpt');
  if (excerptEl) excerptEl.textContent = item.summary || '';
  const metaEl = heroBlock.querySelector('.hero-meta');
  if (metaEl) metaEl.textContent = `${timeText} · گروه ${item.category_fa || meta.label || ''}`;
}

function renderSideList(items, timeText) {
  const sideList = document.querySelector('.side-list');
  if (!sideList) return;
  sideList.innerHTML = items.map(item => {
    const meta = CATEGORY_META[item.category_slug] || {};
    return `
      <div class="side-item">
        <span class="tag ${meta.tagClass || ''}">${escapeHTML(item.category_fa || meta.label || '')}</span>
        <div class="side-title">${escapeHTML(item.title)}</div>
        <div class="side-meta">${timeText}</div>
      </div>`;
  }).join('');
}

function renderTicker(allItems) {
  const tickerMove = document.querySelector('.ticker-move');
  if (!tickerMove || allItems.length === 0) return;
  tickerMove.innerHTML = allItems.map(item => `<span>${escapeHTML(item.title)}</span>`).join('');
}

function renderGrid(slug, item, timeText) {
  const section = document.getElementById(slug);
  if (!section || !item) return; // بدون داده واقعی، گرید دست‌نخورده (نمونه) باقی می‌ماند
  const grid = section.querySelector('.card-grid');
  if (!grid) return;
  const meta = CATEGORY_META[slug] || {};
  grid.innerHTML = `
    <div>
      <div class="card-img" style="position:relative;${imageStyle(item, meta.bg || 'var(--navy-tint)')}">${creditHTML(item)}</div>
      <span class="tag ${meta.tagClass || ''}">${escapeHTML(item.category_fa || meta.label || '')}</span>
      <div class="card-title">${escapeHTML(item.title)}</div>
      <p class="card-excerpt">${escapeHTML(item.summary)}</p>
      <div class="card-meta">${timeText}</div>
    </div>`;
}

function populateSite(data) {
  const news = Array.isArray(data.news) ? data.news : [];
  if (news.length === 0) throw new Error('آرایه اخبار خالی است');

  const timeText = relativeTime(data.generated_at);
  const bySlug = {};
  news.forEach(item => { bySlug[item.category_slug] = item; });

  // هیرو: خبر سیاسی در اولویت است، وگرنه اولین خبر موجود
  const heroItem = bySlug['siasi'] || news[0];

  // نوار کناری: بقیه خبرها به ترتیب SIDE_ORDER (به جز آنکه هیرو شده)
  const sideItems = SIDE_ORDER
    .map(slug => bySlug[slug])
    .filter(item => item && item !== heroItem);

  renderHero(heroItem, timeText);
  renderSideList(sideItems, timeText);
  renderTicker(news);
  ['siasi', 'varzeshi', 'ejtemaei'].forEach(slug => renderGrid(slug, bySlug[slug], timeText));
}

async function loadNews() {
  try {
    const res = await fetch('news/latest.json', { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    populateSite(data);
  } catch (err) {
    console.warn('بارگذاری news/latest.json ناموفق بود؛ متن‌های نمونه فعلی باقی می‌مانند:', err);
  }
}

loadNews();
