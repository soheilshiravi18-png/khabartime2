import os
import sys
import json
from datetime import datetime, timezone
from openai import OpenAI

API_KEY = os.environ["GAPGPT_API_KEY"]
client = OpenAI(base_url="https://api.gapgpt.app/v1", api_key=API_KEY)

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
        # چاپ خروجی خام مدل، تا اگه فرمت خراب بود دقیقاً بدونی مدل چی برگردونده
        print(f"  خروجی خام مدل برای دیباگ:\n{content}\n")
        raise e

    data["category_slug"] = slug
    data["category_fa"] = category_fa
    return data


def main():
    all_news = []
    failures = []

    for slug, category_fa in CATEGORIES.items():
        try:
            item = generate_for_category(slug, category_fa)
            all_news.append(item)
            print(f"✓ خبر دسته '{category_fa}' تولید شد")
        except Exception as e:
            failures.append((category_fa, str(e)))
            print(f"✗ خطا در تولید خبر دسته '{category_fa}': {e}")

    generated_at = datetime.now(timezone.utc).isoformat()
    output = {"generated_at": generated_at, "news": all_news}

    os.makedirs("news", exist_ok=True)

    # نکته‌ی کلیدی: اگه هیچ خبری تولید نشد، فایل latest.json را دست‌نخورده نگه می‌داریم
    # (به‌جای بازنویسی‌اش با آرایه‌ی خالی) و با کد خروجی غیرصفر، اجرا را fail می‌کنیم
    # تا توی GitHub Actions به‌صورت واضح قرمز/failed دیده بشه، نه اینکه ساکت رد بشه.
    if not all_news:
        print("\n هیچ خبری تولید نشد — news/latest.json دست‌نخورده باقی می‌ماند.")
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
        print(f"\nتوجه: {len(failures)} دسته با خطا مواجه شد (ولی چون حداقل یک خبر تولید شد، فایل آپدیت شد):")
        for category_fa, err in failures:
            print(f"  - {category_fa}: {err}")


if __name__ == "__main__":
    main()
