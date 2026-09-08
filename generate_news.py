import os
import sys
import json
import random
import requests
from datetime import datetime, timezone
from openai import OpenAI

API_KEY = os.environ["GAPGPT_API_KEY"]
client = OpenAI(base_url="https://api.gapgpt.app/v1", api_key=API_KEY)

# کلید رایگان از pexels.com/api بگیر و به‌عنوان Secret با همین اسم اضافه کن.
# اگه تعریف نشه، اسکریپت خطا نمی‌ده — فقط بدون عکس ادامه می‌ده (سایت به رنگ پس‌زمینه‌ی قبلی برمی‌گرده).
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

# برای هر دسته، هم برچسب فارسی (برای نمایش) و هم یه عبارت جست‌وجوی انگلیسی
# (برای پیدا کردن عکس مرتبط از Pexels — عکس‌ها بر اساس کلیدواژه‌ی انگلیسی بهتر پیدا می‌شن)
CATEGORIES = {
    "siasi":    {"fa": "سیاسی", "image_query": "government politics building"},
    "varzeshi": {"fa": "ورزشی", "image_query": "sports stadium athlete"},
    "ejtemaei": {"fa": "اجتماعی", "image_query": "city street people community"},
    "dakheli":  {"fa": "داخلی (اقتصاد و بازار)", "image_query": "finance economy market"},
}

SYSTEM_PROMPT = "تو یک خبرنگار حرفه‌ای فارسی‌زبان برای یک وب‌سایت خبری به نام «نبض خبر» هستی. لحن تو رسمی، خبری و بی‌طرف است."


def build_prompt(category_fa: str) -> str:
    return f"""یک خبر کوتاه، قابل‌باور و به‌روز درباره دسته‌بندی «{category_fa}» به زبان فارسی بنویس.
خبر باید عمومی و غیرقابل استناد به رویداد خاص جعلی باشه (از ادعای دقیق درباره افراد یا رویدادهای واقعی که نمی‌تونی تاییدشون کنی خودداری کن؛ می‌تونی خبر رو به‌صورت تحلیلی/روندی بنویسی).
خروجی فقط JSON با این ساختار دقیق باشه (بدون توضیح اضافه، بدون Markdown):
{{
  "title": "عنوان خبر (یک جمله کامل و جذاب)",
  "summary": "خلاصه یک خطی برای نمایش در کارت خبر",
  "body": "متن کامل خبر در ۲ پاراگراف"
}}
"""


def fetch_stock_image(query_en: str):
    """یه عکس واقعی و عمومی (نه مرتبط با یه رویداد ساختگی خاص) بر اساس موضوع دسته از Pexels می‌گیرد.
    اگه کلید تنظیم نشده باشه یا درخواست fail بشه، None برمی‌گردونه (خبر بدون عکس ادامه پیدا می‌کنه)."""
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

    data["category_slug"] = slug
    data["category_fa"] = category_fa

    image = fetch_stock_image(image_query)
    if image:
        data["image_url"] = image["url"]
        data["image_credit"] = image["photographer"]
        data["image_credit_url"] = image["photographer_url"]

    return data


def main():
    all_news = []
    failures = []

    for slug, meta in CATEGORIES.items():
        category_fa = meta["fa"]
        try:
            item = generate_for_category(slug, category_fa, meta["image_query"])
            all_news.append(item)
            has_img = "بله" if item.get("image_url") else "خیر"
            print(f"✓ خبر دسته '{category_fa}' تولید شد (عکس: {has_img})")
        except Exception as e:
            failures.append((category_fa, str(e)))
            print(f"✗ خطا در تولید خبر دسته '{category_fa}': {e}")

    generated_at = datetime.now(timezone.utc).isoformat()
    output = {"generated_at": generated_at, "news": all_news}

    os.makedirs("news", exist_ok=True)

    if not all_news:
        print("\nهیچ خبری تولید نشد — news/latest.json دست‌نخورده باقی می‌ماند.")
        print("جزئیات خطاها:")
        for category_fa, err in failures:
            print(f"  - {category_fa}: {err}")
        sys.exit(1)

    with open("news/latest.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    with open(f"news/archive_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{len(all_news)} خبر تولید و در news/latest.json ذخیره شد")

    if failures:
        print(f"\nتوجه: {len(failures)} دسته با خطا مواجه شد:")
        for category_fa, err in failures:
            print(f"  - {category_fa}: {err}")


if __name__ == "__main__":
    main()
