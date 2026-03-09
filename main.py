import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# Логларни созлаш
logging.basicConfig(level=logging.INFO)

# --- СОЗЛАМАЛАР ---
API_TOKEN = '8614302276:AAFNVLBBxKclvOrSmV5GHHYfg6vEOZsESo' 
ADMIN_ID = 58170268 
ADMIN_PHONE = "+998 91 404 15 15"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# МАЪЛУМОТЛАР
MENU = {"🍔 Чизбургер": 35000, "🍔 Гамбургер": 30000, "🥤 Pepsi 1.5L": 15000}
user_data = {} 
temp_data = {}

# --- RENDER УЧУН WEB SERVER ҚИСМИ ---
async def handle(request):
    return web.Response(text="Бот ишлаяпти!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render тақдим этадиган PORT-ни оламиз ёки 10000-ни ишлатамиз
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server {port} портда ишга тушди.")

# --- БОТ ЛОГИКАСИ ---
def get_user_storage(uid):
    if uid not in user_data:
        user_data[uid] = {"items": [], "lat": None, "lon": None, "state": None, "last_item": None}
    return user_data[uid]

def main_menu(uid):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🍴 Меню"))
    builder.row(types.KeyboardButton(text="🛒 Саватча"), types.KeyboardButton(text="📞 Алоқа"))
    if uid == ADMIN_ID:
        builder.row(types.KeyboardButton(text="⚙️ Админ Панель"))
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    get_user_storage(message.from_user.id)
    await message.answer("🍔 **The Cheff Burger** ботига хуш келибсиз!", reply_markup=main_menu(message.from_user.id))

@dp.message(F.text == "📞 Алоқа")
async def contact_info(message: types.Message):
    await message.answer(f"👨‍💻 **Админ билан боғланиш:**\n\n☎️ Тел: {ADMIN_PHONE}\n💬 Телеграм: @TheCheffAdmin")

@dp.message(F.text == "🍴 Меню")
async def show_menu(message: types.Message):
    builder = ReplyKeyboardBuilder()
    for item, price in MENU.items():
        builder.row(types.KeyboardButton(text=f"{item} - {price:,} сўм"))
    builder.row(types.KeyboardButton(text="⬅️ Ортга"))
    await message.answer("Маҳсулот танланг:", reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.text.contains(" - ") & F.text.contains("сўм"))
async def ask_quantity(message: types.Message):
    uid = message.from_user.id
    name = message.text.split(" - ")[0]
    if name in MENU:
        data = get_user_storage(uid)
        data["last_item"] = name
        data["state"] = "wait_qty"
        builder = ReplyKeyboardBuilder()
        for i in range(1, 10): builder.add(types.KeyboardButton(text=str(i)))
        builder.row(types.KeyboardButton(text="⬅️ Ортга"))
        await message.answer(f"🔢 {name} дан нечта керак?", reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(lambda m: get_user_storage(m.from_user.id).get("state") == "wait_qty")
async def add_to_cart(message: types.Message):
    uid = message.from_user.id
    data = get_user_storage(uid)
    if message.text == "⬅️ Ортга":
        data["state"] = None
        await show_menu(message); return
    try:
        qty = int(message.text)
        data["items"].append({"name": data["last_item"], "price": MENU[data["last_item"]], "qty": qty})
        data["state"] = None
        await message.answer(f"✅ Саватчага қўшилди.", reply_markup=main_menu(uid))
    except: await message.answer("Фақат рақам юборинг.")

@dp.message(F.text == "🛒 Саватча")
async def view_cart(message: types.Message):
    data = get_user_storage(message.from_user.id)
    if not data["items"]:
        await message.answer("Саватча бўш."); return
    res = "🛒 **Саватчангиз:**\n\n"
    total = 0
    for i, item in enumerate(data["items"], 1):
        sub = item['price'] * item['qty']
        res += f"{i}. {item['name']} x {item['qty']} = {sub:,}\n"
        total += sub
    res += f"\n💰 Жами: {total:,} сўм"
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🚖 Буюртма бериш"), types.KeyboardButton(text="🗑 Тозалаш"))
    builder.row(types.KeyboardButton(text="⬅️ Ортга"))
    await message.answer(res, reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.text == "🗑 Тозалаш")
async def clear_cart(message: types.Message):
    data = get_user_storage(message.from_user.id)
    data["items"] = []
    await message.answer("Саватча тозаланди.", reply_markup=main_menu(message.from_user.id))

@dp.message(F.text == "🚖 Буюртма бериш")
async def order(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📍 Локация", request_location=True))
    builder.row(types.KeyboardButton(text="📱 Телефон", request_contact=True))
    await message.answer("Локация ва телефон юборинг:", reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.location)
async def handle_loc(message: types.Message):
    data = get_user_storage(message.from_user.id)
    data["lat"], data["lon"] = message.location.latitude, message.location.longitude
    await bot.send_message(ADMIN_ID, f"📍 Локация келди: {message.from_user.full_name}")
    await bot.send_location(ADMIN_ID, data["lat"], data["lon"])
    await message.answer("✅ Локация қабул қилинди. Энди телефон рақамингизни юборинг.")

@dp.message(F.contact)
async def handle_con(message: types.Message):
    uid = message.from_user.id
    data = get_user_storage(uid)
    if not data["items"]: return
    txt = f"🔔 **ЯНГИ БУЮРТМА!**\n👤 {message.from_user.full_name}\n📞 {message.contact.phone_number}\n\n"
    total = 0
    for item in data["items"]:
        sub = item['price'] * item['qty']
        txt += f"- {item['name']} ({item['qty']} та)\n"
        total += sub
    txt += f"\n💰 Жами: {total:,} сўм"
    await bot.send_message(ADMIN_ID, txt)
    await message.answer("✅ Буюртма юборилди!", reply_markup=main_menu(uid))
    data["items"] = []

@dp.message(F.text == "⚙️ Админ Панель")
async def admin(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Қўшиш", callback_data="add")
    builder.button(text="🗑 Ўчириш", callback_data="del")
    await message.answer("Бошқарув:", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "add")
async def add(c: types.CallbackQuery):
    temp_data[ADMIN_ID] = "name"
    await c.message.answer("Номини ёзинг:"); await c.answer()

@dp.message(lambda m: temp_data.get(ADMIN_ID) == "name")
async def s_name(m: types.Message):
    temp_data["n"] = m.text; temp_data[ADMIN_ID] = "price"
    await m.answer("Нархини ёзинг:")

@dp.message(lambda m: temp_data.get(ADMIN_ID) == "price")
async def s_price(m: types.Message):
    try:
        MENU[temp_data["n"]] = int(m.text)
        temp_data[ADMIN_ID] = None
        await m.answer("✅ Қўшилди!", reply_markup=main_menu(ADMIN_ID))
    except: await m.answer("Рақам ёзинг!")

@dp.callback_query(F.data == "del")
async def d_list(c: types.CallbackQuery):
    b = InlineKeyboardBuilder()
    for k in MENU.keys(): b.button(text=f"❌ {k}", callback_data=f"r_{k}")
    b.adjust(1)
    await c.message.edit_text("Ўчириш:", reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("r_"))
async def remove(c: types.CallbackQuery):
    n = c.data.replace("r_", "")
    if n in MENU: del MENU[n]
    await admin(c.message); await c.answer()

@dp.message(F.text == "⬅️ Ортга")
async def back(m: types.Message):
    await m.answer("Бош меню.", reply_markup=main_menu(m.from_user.id))

# --- АСОСИЙ ИШГА ТУШИРИШ ---
async def main():
    # Бир вақтда ҳам веб-серверни, ҳам ботни ишга туширамиз
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
