import os
import json
from datetime import datetime
from openai import OpenAI

API_KEY = os.environ["GAPGPT_API_KEY"]

client = OpenAI(base_url="https://api.gapgpt.app/v1", api_key=API_KEY)

# دسته‌بندی‌های سایت - می‌تونی این لیست رو ویرایش کنی
CATEGORIES = {
    "siasi": "سیاسی",
    "varzeshi": "ورزشی",
    "ejtemaei": "اجتماعی",
    "dakheli": "داخلی (اقتصاد و بازار)",
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

def generate_for_category(slug: str, category_fa: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(category_fa)}
        ]
    )
    content = response.choices[0].message.content.strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    data = json.loads(content)
    data["category_slug"] = slug
    data["category_fa"] = category_fa
    return data

def main():
    all_news = []
    for slug, category_fa in CATEGORIES.items():
        try:
            item = generate_for_category(slug, category_fa)
            all_news.append(item)
            print(f"✓ خبر دسته '{category_fa}' تولید شد")
        except Exception as e:
            print(f"✗ خطا در تولید خبر دسته '{category_fa}': {e}")

    generated_at = datetime.utcnow().isoformat()

    output = {
        "generated_at": generated_at,
        "news": all_news
    }

    os.makedirs("news", exist_ok=True)

    # فایل آخرین اخبار - همیشه بازنویسی می‌شود (برای نمایش در سایت)
    with open("news/latest.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # آرشیو با تاریخ (برای نگهداری تاریخچه)
    date_str = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
    with open(f"news/archive_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{len(all_news)} خبر تولید و در news/latest.json ذخیره شد")

if __name__ == "__main__":
    main()
