import asyncio
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.bot import DefaultBotProperties

# -----------------------
# BOT TOKEN
# -----------------------
BOT_TOKEN = "7622509160:AAGqpeR6m1A7zF2k-k9ej7jFy7koDQLHdKU"

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

# -----------------------
# CHECK PAYMENT GATEWAY
# -----------------------
def check_for_payment_gateway(headers, content_type, cookies, html):
    gateway_keywords = {
        'mollie': ['mollie', 'mollie.com'],
        'square': ['squareup', 'squareup.com'],
        'cybersource': ['cybersource'],
        '2checkout': ['2checkout', '2co.com'],
        'eway': ['eway'],
        'stripe': ['stripe', 'stripe.js'],
        'paypal': ['paypal', 'paypal.com', 'paypalobjects'],
        'braintree': ['braintree'],
        'worldpay': ['worldpay'],
        'authnet': ['authorize.net', 'authnet'],
        'recurly': ['recurly'],
        'shopify': ['shopify', 'myshopify.com'],
        'adyen': ['adyen'],
        'payu': ['payu', 'payu.in', 'payumoney.com', 'secure.payu'],
        'razorpay': ['razorpay', 'razorpay.com', 'checkout.razorpay.com']
    }

    found = []
    for keyword, values in gateway_keywords.items():
        if (
            keyword in content_type.lower()
            or any(v.lower() in html or v.lower() in str(cookies) for v in values)
        ):
            found.append(keyword.capitalize())

    return found


# -----------------------
# CHECK GRAPHQL
# -----------------------
def check_for_graphql(html: str) -> bool:
    return any(k in html.lower() for k in ["graphql", "gql"])


# -----------------------
# CHECK CAPTCHA
# -----------------------
def check_for_captcha(html: str) -> bool:
    keys = ["captcha", "g-recaptcha", "recaptcha", "data-sitekey", "arkoselabs"]
    return any(k in html.lower() for k in keys)


# -----------------------
# ANALYZE SITE
# -----------------------
def analyze_site(site: str) -> dict:
    result = {
        "gateway": [],
        "cloudflare": False,
        "captcha": False,
        "platform": None,
        "graphql": False,
        "urls": []
    }

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(site, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        page_texts = [r.text.lower()]
        all_html = r.text

        content_type = r.headers.get("Content-Type", "")
        cookies = r.cookies

        found = False

        for a in soup.find_all("a", href=True):
            link = a["href"].lower()
            if any(x in link for x in ["checkout", "cart", "payment"]):
                try:
                    full = urljoin(site, link)
                    r2 = requests.get(full, headers=headers, timeout=10)
                    all_html += r2.text
                    page_texts.append(r2.text.lower())
                    result["urls"].append(full)
                    found = True
                except:
                    pass

        if not found:
            result["urls"].append(site)

        full_text = " ".join(page_texts)

        result["gateway"] = check_for_payment_gateway(r.headers, content_type, cookies, all_html)
        result["graphql"] = check_for_graphql(all_html)
        result["captcha"] = check_for_captcha(all_html)

        if any(k in full_text for k in ["cloudflare", "cf-ray", "__cfduid", "cf_clearance"]):
            result["cloudflare"] = True

        if "shopify" in full_text:
            result["platform"] = "Shopify"
        elif "woocommerce" in full_text:
            result["platform"] = "WooCommerce"
        elif "bigcommerce" in full_text:
            result["platform"] = "BigCommerce"
        elif "magento" in full_text:
            result["platform"] = "Magento"

    except Exception as e:
        result["error"] = str(e)

    return result


# -----------------------
# FORMAT RESULT
# -----------------------
def format_result(result: dict, m):
    if "error" in result:
        return f"❌ Error: {result['error']}"

    urls = result.get("urls", [])
    first = f"<code>{urls[0]}</code>" if urls else "<code>None</code>"

    return f"""
<b>ALFU | Gateway Scanner 🔥</b>

[ϟ] Gateways: <code>{', '.join(result['gateway']) or 'None'}</code>
[ϟ] Captcha: <code>{'True 😭' if result['captcha'] else 'False 🔥'}</code>
[ϟ] Cloudflare: <code>{'True 😭' if result['cloudflare'] else 'False 🔥'}</code>
[ϟ] GraphQL: <code>{'True 😭' if result['graphql'] else 'False 🔥'}</code>
[ϟ] Platform: <code>{result['platform'] or 'Unknown'}</code>
[ϟ] URL: {first}

Checked by: <a href='tg://user?id={m.from_user.id}'>{m.from_user.first_name}</a>
"""


# -----------------------
# ⭐ /start WITH BUTTONS
# -----------------------
@dp.message(Command("start"))
async def start_cmd(m: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔍 Check URL", callback_data="chk_btn")
    kb.button(text="ℹ️ Help", callback_data="help_btn")
    kb.adjust(1)

    await m.answer(
        f"Hello <b>{m.from_user.first_name}</b>! 👋\n"
        f"Welcome to <b>ALFU Site Checker Bot</b> 🔥\n\n"
        "<b>USE /url TO CHECK SITE 👇</b>",
        reply_markup=kb.as_markup()
    )


# -----------------------
# BUTTON CALLBACKS
# -----------------------
@dp.callback_query(lambda c: c.data == "chk_btn")
async def chk_btn_handler(c: types.CallbackQuery):
    await c.message.answer("Use this command:\n<code>/url example.com</code>")
    await c.answer()


@dp.callback_query(lambda c: c.data == "help_btn")
async def help_btn_handler(c: types.CallbackQuery):
    await c.message.answer(
        "📌 <b>Help Menu</b>\n\n"
        "/start – Show menu\n"
        "/url site.com – Scan website\n"
        "More features coming soon 🔥"
    )
    await c.answer()


# -----------------------
# /url COMMAND (AUTO ADD HTTPS)
# -----------------------
@dp.message(Command("url"))
async def url_cmd(m: types.Message):
    args = m.text.split()
    if len(args) < 2:
        return await m.reply("Usage: /url example.com")

    site = args[1]

    # AUTO HTTPS FIX  
    if not site.startswith("http://") and not site.startswith("https://"):
        site = "https://" + site

    result = analyze_site(site)
    await m.reply(format_result(result, m))


# -----------------------
# RUN BOT
# -----------------------
async def main():
    print("🚀 Bot Running…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())