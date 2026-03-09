import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# 1. СОЗЛАМАЛАР
# Сиз берган янги токен
API_TOKEN = '8614302276:AAHzG09FGl-4R5r4_4VNSfOD0Oemhlshfbs'
# Сизнинг Telegram ID-нгиз (Админ панель кўриниши учун)
ADMIN_ID = 58170268 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# 2. МАЪЛУМОТЛАР (МEНЮ)
MENU = {
    "🍔 Чизбургер": 35000, 
    "🍔 Гамбургер": 30000, 
    "🥤 Pepsi 1.5L": 15000,
    "🍟 Фри": 15000
}
user_cart = {} # Фойдаланувчи саватчаси

# 3. RENDER УЧУН ВEБ СEРВEР (Port scan timeout хатосини олдини олади)
async def handle(request):
    return web.Response(text="TheCheffBurger Bot ишлаяпти!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Вeб-сeрвeр {port}-портда фаол.")

# 4. КЛАВИАТУРАЛАР
def main_menu_kb(uid):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🍴 Меню"))
    builder.row(types.KeyboardButton(text="🛒 Саватча"), types.KeyboardButton(text="📞 Алоқа"))
    if uid == ADMIN_ID:
        builder.row(types.KeyboardButton(text="⚙️ Админ Панель"))
    return builder.as_markup(resize_keyboard=True)

# 5. БОТ КОМАНДАЛАРИ
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    uid = message.from_user.id
    user_cart[uid] = []
    await message.answer(
        f"🍔 **The Cheff Burger** ботига хуш келибсиз, {message.from_user.first_name}!",
        reply_markup=main_menu_kb(uid)
    )

@dp.message(F.text == "🍴 Меню")
async def show_menu(message: types.Message):
    builder = ReplyKeyboardBuilder()
    for item, price in MENU.items():
        builder.row(types.KeyboardButton(text=f"{item} - {price:,} сўм"))
    builder.row(types.KeyboardButton(text="⬅️ Ортга"))
    await message.answer("Маҳсулот танланг:", reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.text == "⚙️ Админ Панель")
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 **Админ Панель:**\n\n1. Буюртмалар статистикаси\n2. Менюни таҳрирлаш\n3. Хабарнома юбориш")
    else:
        await message.answer("🚫 Сиз админ эмассиз!")

@dp.message(F.text == "📞 Алоқа")
async def contact(message: types.Message):
    await message.answer("👨‍💻 Саволлар бўлса админга ёзинг: @TheCheffAdmin\n📞 Тел: +998 91 404 15 15")

@dp.message(F.text == "⬅️ Ортга")
async def go_back(message: types.Message):
    await message.answer("Бош меню", reply_markup=main_menu_kb(message.from_user.id))

# 6. АСОСИЙ ИШГА ТУШИРИШ
async def main():
    # Веб-сервер ва ботни бир вақтда юргазиш
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())

