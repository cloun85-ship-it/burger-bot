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
# Сизнинг амалдаги токенингиз
API_TOKEN = '8614302276:AAFNVLBBxKclvOrSmV5GHHYfg6vEOZsESo' 
ADMIN_ID = 58170268 
ADMIN_PHONE = "+998 91 404 15 15"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# МАЪЛУМОТЛАР (МEНЮ)
MENU = {
    "🍔 Чизбургер": 35000, 
    "🍔 Гамбургер": 30000, 
    "🥤 Pepsi 1.5L": 15000,
    "🍟 Фри": 15000
}
user_data = {} 
temp_data = {}

# --- RENDER УЧУН ВEБ СEРВEР ҚИСМИ ---
# Бу қисм "No open ports detected" хатосини олдини олади
async def handle(request):
    return web.Response(text="TheCheffBurger Bot ишлаяпти!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render тақдим этадиган PORT ўзгарувчисини оламиз
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Вeб-сeрвeр {port}-портда ишга тушди.")

# --- БОТ ФУНКЦИЯЛАРИ ---
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
        res += f"{i}. {item['name']} x {item['qty']} = {sub:,} сўм\n"
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
    builder.row(types.KeyboardButton(text="📍 Локация юбориш", request_location=True))
    builder.row(types.KeyboardButton(text="📱 Тeлeфон юбориш", request_contact=True))
    await message.answer("Буюртмани якунлаш учун локация ва тeлeфон рақамингизни юборинг:", reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.location)
async def handle_loc(message: types.Message):
    data = get_user_storage(message.from_user.id)
    data["lat"], data["lon"] = message.location.latitude, message.location.longitude
    await message.answer("✅ Локация қабул қилинди. Энди телефон рақамингизни юборинг (пастдаги тугма орқали).")

@dp.message(F.contact)
async def handle_con(message: types.Message):
    uid = message.from_user.id
    data = get_user_storage(uid)
    if not data["items"]:
        await message.answer("Саватчангиз бўш!"); return
    
    txt = f"🔔 **ЯНГИ БУЮРТМА!**\n👤 {message.from_user.full_name}\n📞 {message.contact.phone_number}\n\n"
    total = 0
    for item in data["items"]:
        sub = item['price'] * item['qty']
        txt += f"- {item['name']} ({item['qty']} та)\n"
        total += sub
    txt += f"\n💰 Жами: {total:,} сўм"
    
    # Админга юбориш
    await bot.send_message(ADMIN_ID, txt)
    if data["lat"]:
        await bot.send_location(ADMIN_ID, data["lat"], data["lon"])
    
    await message.answer("✅ Буюртмангиз қабул қилинди! Тез орада боғланамиз.", reply_markup=main_menu(uid))
    data["items"] = [] # Саватчани тозалаш

@dp.message(F.text == "⬅️ Ортга")
async def back(m: types.Message):
    await m.answer("Бош меню.", reply_markup=main_menu(m.from_user.id))

# --- АСОСИЙ ИШГА ТУШИРИШ ---
async def main():
    # Вeб-сeрвeр ва Ботни параллел равишда юргазиш
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Бот тўхтатилди!")
