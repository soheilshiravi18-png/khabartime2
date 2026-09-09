import os
import sys
import json
import random
import uuid
import requests
from datetime import datetime, timezone, timedelta
from openai import OpenAI

API_KEY = os.environ["GAPGPT_API_KEY"]
client = OpenAI(base_url="https://api.gapgpt.app/v1", api_key=API_KEY)

# کلید رایگان از pexels.com/api بگیر و به‌عنوان Secret با همین اسم اضافه کن.
# اگه تعریف نشه، اسکریپت خطا نمی‌ده — فقط بدون عکس ادامه می‌ده.
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

# این اسکریپت فقط یک fallback است: اگر ربات تلگرام طی این چند ساعت اخیر خبر واقعی
# نفرستاده باشد، چند خبر عمومی/غیرقابل‌استناد تولید می‌کند تا سایت کاملاً خالی نماند.
# اگر خبر واقعی تازه (از ربات، source == "telegram") موجود باشد، این اسکریپت هیچ کاری
# نمی‌کند و بدون خطا خارج می‌شود.
FALLBACK_THRESHOLD_HOURS = float(os.environ.get("FALLBACK_THRESHOLD_HOURS", "6"))
NEWS_FILE = "news/latest.json"
MAX_NEWS_ITEMS = int(os.environ.get("MAX_WEBSITE_NEWS_ITEMS", "80"))

# برای هر دسته، هم برچسب فارسی (برای نمایش) و هم یه عبارت جست‌وجوی انگلیسی برای Pexels.
# این اسلاگ‌ها باید دقیقاً با CATEGORY_META در news-loader.js یکی باشند.
CATEGORIES = {
    "siasi":    {"fa": "سیاسی", "image_query": "government politics building"},
    "varzeshi": {"fa": "ورزشی", "image_query": "sports stadium athlete"},
    "ejtemaei": {"fa": "اجتماعی", "image_query": "city street people community"},
    "dakheli":  {"fa": "اقتصادی", "image_query": "finance economy market"},
}

SYSTEM_PROMPT = "تو یک خبرنگار حرفه‌ای فارسی‌زبان برای یک وب‌سایت خبری به نام «نبض خبر» هستی. لحن تو رسمی، خبری و بی‌طرف است."


def build_prompt(category_fa: str) -> str:
    return f"""یک خبر کوتاه، قابل‌باور و به‌روز درباره دسته‌بندی «{category_fa}» به زبان فارسی بنویس.
خبر باید عمومی و غیرقابل استناد به رویداد خاص جعلی باشه (از ادعای دقیق درباره افراد یا رویدادهای واقعی که نمی‌تونی تاییدشون کنی خودداری کن؛ می‌تونی خبر رو به‌صورت تحلیلی/روندی بنویسی).
خروجی فقط JSON با این ساختار دقیق باشه (بدون توضیح اضافه، بدون Markdown):
{{
  "title": "عنوان خبر (یک جمله کامل و جذاب)",
  "summary": "خلاصه یک خطی برای نمایش در کارت خبر"
}}
"""


def fetch_stock_image(query_en: str):
    if not PEXELS_API_KEY:
        return None
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query_en, "per_page": 15, "orientation": "landscape"},
            timeout=10,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            return None
        photo = random.choice(photos)
        return {
            "url": photo["src"]["large"],
            "photographer": photo.get("photographer"),
            "photographer_url": photo.get("photographer_url"),
        }
    except Exception as e:
        print(f"  هشدار: دریافت عکس استوک برای '{query_en}' ناموفق بود: {e}")
        return None


def generate_for_category(slug: str, category_fa: str, image_query: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(category_fa)},
        ],
    )
    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"  خروجی خام مدل برای دیباگ:\n{content}\n")
        raise e

    image = fetch_stock_image(image_query)

    return {
        "id": str(uuid.uuid4()),
        "title": data.get("title", ""),
        "summary": data.get("summary", ""),
        "category_slug": slug,
        "category_fa": category_fa,
        "image_url": image["url"] if image else None,
        "image_credit": image["photographer"] if image else None,
        "image_credit_url": image["photographer_url"] if image else None,
        "source": "auto-generated",
        "published_at": datetime.now(timezone.utc).isoformat(),
    }


def load_existing():
    try:
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("news", []) if isinstance(data, dict) else []
    except Exception:
        return []


def most_recent_real_news_time(existing_news):
    times = []
    for item in existing_news:
        # آیتم‌های قدیمی که از این اسکریپت خودش ساخته شده‌اند (بدون source یا source == auto-generated)
        # «واقعی» حساب نمی‌شوند — فقط source == "telegram" باعث توقف fallback می‌شود.
        if item.get("source") != "telegram":
            continue
        ts = item.get("published_at")
        if not ts:
            continue
        try:
            times.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
        except Exception:
            continue
    return max(times) if times else None


def main():
    existing_news = load_existing()
    latest_real = most_recent_real_news_time(existing_news)

    if latest_real is not None:
        age_hours = (datetime.now(timezone.utc) - latest_real).total_seconds() / 3600
        if age_hours < FALLBACK_THRESHOLD_HOURS:
            print(
                f"آخرین خبر واقعی از تلگرام {age_hours:.1f} ساعت پیش رسیده "
                f"(آستانه: {FALLBACK_THRESHOLD_HOURS} ساعت) — نیازی به خبر جایگزین نیست. خارج می‌شویم."
            )
            return

    print("خبر واقعی تازه‌ای از تلگرام پیدا نشد — در حال تولید چند خبر جایگزین (fallback)...")

    new_items = []
    failures = []
    for slug, meta in CATEGORIES.items():
        category_fa = meta["fa"]
        try:
            item = generate_for_category(slug, category_fa, meta["image_query"])
            new_items.append(item)
            has_img = "بله" if item.get("image_url") else "خیر"
            print(f"✓ خبر جایگزین دسته '{category_fa}' تولید شد (عکس: {has_img})")
        except Exception as e:
            failures.append((category_fa, str(e)))
            print(f"✗ خطا در تولید خبر دسته '{category_fa}': {e}")

    if not new_items:
        print("\nهیچ خبر جایگزینی تولید نشد — news/latest.json دست‌نخورده باقی می‌ماند.")
        for category_fa, err in failures:
            print(f"  - {category_fa}: {err}")
        sys.exit(1 if failures else 0)

    # به آرایه‌ی موجود اضافه می‌شود، نه جایگزین آن — اخبار واقعیِ قبلی پاک نمی‌شوند.
    combined = (new_items + existing_news)[:MAX_NEWS_ITEMS]
    output = {"generated_at": datetime.now(timezone.utc).isoformat(), "news": combined}

    os.makedirs("news", exist_ok=True)
    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    with open(f"news/archive_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{len(new_items)} خبر جایگزین اضافه شد. مجموع اخبار سایت: {len(combined)}")
    if failures:
        print(f"\nتوجه: {len(failures)} دسته با خطا مواجه شد:")
        for category_fa, err in failures:
            print(f"  - {category_fa}: {err}")


if __name__ == "__main__":
    main()
