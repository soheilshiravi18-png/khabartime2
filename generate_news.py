import os
import json
from datetime import datetime
from openai import OpenAI

API_KEY = os.environ["GAPGPT_API_KEY"]

client = OpenAI(base_url="https://api.gapgpt.app/v1", api_key=API_KEY)

# موضوع خبر - می‌تونی این رو عوض کنی یا از یه لیست موضوعات بخونی
TOPIC = "آخرین اخبار تکنولوژی و هوش مصنوعی"

PROMPT = f"""یک خبر کوتاه و حرفه‌ای درباره موضوع زیر به زبان فارسی بنویس.
موضوع: {TOPIC}

قالب خروجی باید JSON باشه با این ساختار دقیق (فقط JSON، بدون توضیح اضافه):
{{
  "title": "عنوان خبر",
  "summary": "خلاصه یک خطی",
  "body": "متن کامل خبر در ۲ تا ۳ پاراگراف"
}}
"""

def generate_news():
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "تو یک خبرنگار حرفه‌ای فارسی‌زبان هستی."},
            {"role": "user", "content": PROMPT}
        ]
    )
    content = response.choices[0].message.content

    # پاک کردن فرمت مارک‌داون احتمالی دور JSON
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    news_data = json.loads(content)
    news_data["generated_at"] = datetime.utcnow().isoformat()
    return news_data

if __name__ == "__main__":
    news = generate_news()

    # ذخیره در فایل با تاریخ امروز
    date_str = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
    output_dir = "news"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{date_str}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)

    print(f"خبر تولید و ذخیره شد: {output_path}")
    print(json.dumps(news, ensure_ascii=False, indent=2))
