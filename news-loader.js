// news-loader.js
// محتوای واقعی news/latest.json را جایگزین متن‌های نمونه سایت می‌کند.
// این فایل حالا با «تعداد رو به رشد» خبر در هر دسته کار می‌کند (نه فقط یک خبر ثابت per دسته)،
// چون ربات تلگرام هر خبر تازه را جلوی آرایه اضافه می‌کند (جدیدترین = news[0]).

const CATEGORY_META = {
  siasi:     { tagClass: 'tag-siasi',     label: 'سیاسی',            bg: 'var(--navy-tint)' },
  varzeshi:  { tagClass: 'tag-varzeshi',  label: 'ورزشی',            bg: 'var(--green-tint)' },
  ejtemaei:  { tagClass: 'tag-ejtemaei',  label: 'اجتماعی',          bg: 'var(--gold-tint)' },
  dakheli:   { tagClass: 'tag-dakheli',   label: 'اقتصادی',          bg: 'var(--coral-tint)' },
  khareji:   { tagClass: 'tag-khareji',   label: 'بین‌الملل',        bg: 'var(--blue-tint)' },
  fanavari:  { tagClass: 'tag-fanavari',  label: 'فناوری',           bg: 'var(--teal-tint)' },
  farhangi:  { tagClass: 'tag-farhangi',  label: 'فرهنگی و هنری',    bg: 'var(--purple-tint)' },
  salamat:   { tagClass: 'tag-salamat',   label: 'سلامت',            bg: 'var(--rose-tint)' },
  havades:   { tagClass: 'tag-havades',   label: 'حوادث',            bg: 'var(--orange-tint)' },
  sayer:     { tagClass: 'tag-sayer',     label: 'سایر',             bg: 'var(--hair)' },
};

// ترتیب دسته‌هایی که در نوار کناری (side-list) اگر جای خالی باشد نمایش داده می‌شوند —
// در عمل الان side-list دیگر به این ترتیب وابسته نیست (بر اساس تازگی پر می‌شود)، فقط برای fallback نگه داشته شده.
const CARDS_PER_SECTION = 6;
const SIDE_LIST_COUNT = 4;
const TICKER_COUNT = 15;

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

// عکس واقعی -> background-image؛ وگرنه رنگ تینت پیش‌فرض همان دسته
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

// خبرهایی که واقعاً از تلگرام آمده‌اند source:'telegram' دارند.
// خبرهای «سایتی که هنوز خبر واقعی نرسیده» (auto-generated) با یک نشان کوچک متمایز می‌شوند
// تا با اخبار واقعی قاطی نشوند.
function sourceBadgeHTML(item) {
  if (item && item.source === 'auto-generated') {
    return `<span style="font-size:10px;color:var(--ink-soft);border:1px solid var(--hair);border-radius:3px;padding:1px 6px;margin-inline-start:6px;">خودکار</span>`;
  }
  return '';
}

function itemTime(item) {
  return item.published_at || item.generated_at || null;
}

function renderHero(item) {
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
  if (metaEl) metaEl.textContent = `${relativeTime(itemTime(item))} · گروه ${item.category_fa || meta.label || ''}`;
}

function renderSideList(items) {
  const sideList = document.querySelector('.side-list');
  if (!sideList) return;
  sideList.innerHTML = items.map(item => {
    const meta = CATEGORY_META[item.category_slug] || {};
    return `
      <div class="side-item">
        <span class="tag ${meta.tagClass || ''}">${escapeHTML(item.category_fa || meta.label || '')}</span>${sourceBadgeHTML(item)}
        <div class="side-title">${escapeHTML(item.title)}</div>
        <div class="side-meta">${relativeTime(itemTime(item))}</div>
      </div>`;
  }).join('');
}

function renderTicker(items) {
  const tickerMove = document.querySelector('.ticker-move');
  if (!tickerMove || items.length === 0) return;
  tickerMove.innerHTML = items.slice(0, TICKER_COUNT).map(item => `<span>${escapeHTML(item.title)}</span>`).join('');
}

// حالا هر بخش (مثلاً «سیاسی») چند کارت آخرِ همان دسته را نشان می‌دهد، نه فقط یک خبر تکراری.
function renderGrid(slug, items) {
  const section = document.getElementById(slug);
  if (!section) return;

  if (!items.length) {
    // هیچ خبر واقعی‌ای در این دسته هنوز نیامده — کل بخش را مخفی می‌کنیم
    // تا به‌جایش متن‌های نمونه‌ی همیشگی و ثابت نمایش داده نشوند.
    section.style.display = 'none';
    return;
  }
  section.style.display = '';

  const grid = section.querySelector('.card-grid');
  if (!grid) return;
  const meta = CATEGORY_META[slug] || {};

  grid.innerHTML = items.slice(0, CARDS_PER_SECTION).map(item => `
    <div>
      <div class="card-img" style="position:relative;${imageStyle(item, meta.bg || 'var(--navy-tint)')}">${creditHTML(item)}</div>
      <span class="tag ${meta.tagClass || ''}">${escapeHTML(item.category_fa || meta.label || '')}</span>${sourceBadgeHTML(item)}
      <div class="card-title">${escapeHTML(item.title)}</div>
      <p class="card-excerpt">${escapeHTML(item.summary)}</p>
      <div class="card-meta">${relativeTime(itemTime(item))}</div>
    </div>`).join('');
}

function populateSite(data) {
  const rawNews = Array.isArray(data.news) ? data.news : [];
  if (rawNews.length === 0) throw new Error('آرایه اخبار خالی است');

  // مرتب‌سازی بر اساس تازگی (جدیدترین اول) — مستقل از ترتیبی که در فایل ذخیره شده
  const news = [...rawNews].sort((a, b) => {
    const ta = new Date(itemTime(a) || 0).getTime();
    const tb = new Date(itemTime(b) || 0).getTime();
    return tb - ta;
  });

  // هیرو: جدیدترین خبر سیاسی در اولویت است، وگرنه جدیدترین خبر کلی
  const heroItem = news.find(item => item.category_slug === 'siasi') || news[0];

  // نوار کناری: جدیدترین خبرهای دیگر (از هر دسته‌ای)، به‌جز خودِ هیرو
  const sideItems = news.filter(item => item !== heroItem).slice(0, SIDE_LIST_COUNT);

  renderHero(heroItem);
  renderSideList(sideItems);
  renderTicker(news);

  Object.keys(CATEGORY_META).forEach(slug => {
    const itemsForSlug = news.filter(item => item.category_slug === slug);
    renderGrid(slug, itemsForSlug);
  });
}

async function loadNews() {
  try {
    const res = await fetch('news/latest.json', { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    populateSite(data);
    const lastUpdateEl = document.getElementById('lastUpdate');
    if (lastUpdateEl && data.generated_at) {
      const d = new Date(data.generated_at);
      if (!isNaN(d.getTime())) {
        lastUpdateEl.textContent = d.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });
      }
    }
  } catch (err) {
    console.warn('بارگذاری news/latest.json ناموفق بود؛ متن‌های نمونه فعلی باقی می‌مانند:', err);
  }
}

loadNews();
// هر ۶۰ ثانیه دوباره چک می‌کند تا اگر کاربر صفحه را باز نگه داشته، خبر تازه بدون رفرش دستی هم دیده شود.
setInterval(loadNews, 60000);
