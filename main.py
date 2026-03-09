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
# Сизнинг шахсий Telegram ID-нгиз (image_231d5a.png дан олинди)
ADMIN_ID = 58170268 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# 2. RENDER УЧУН ВEБ СEРВEР (Порт хатосини олдини олиш учун)
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

# 3. КЛАВИАТУРА (МEНЮ)
def main_menu_kb(uid):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🍴 Меню"))
    builder.row(types.KeyboardButton(text="🛒 Саватча"), types.KeyboardButton(text="📞 Алоқа"))
    # Айнан сиз учун Админ Панель тугмасини чиқариш
    if uid == ADMIN_ID:
        builder.row(types.KeyboardButton(text="⚙️ Админ Панель"))
    return builder.as_markup(resize_keyboard=True)

# 4. БОТ ХEНДЛEРЛАРИ
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    uid = message.from_user.id
    await message.answer(
        f"🍔 **The Cheff Burger** ботига хуш келибсиз!",
        reply_markup=main_menu_kb(uid)
    )

@dp.message(F.text == "⚙️ Админ Панель")
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "🛠 **Админ Бошқарув Панели**\n\n"
            "Бу ерда сиз буюртмаларни кўришингиз ва менюни бошқаришингиз мумкин.\n"
            "(Қўшимча функцияларни шу ерга қўшиш мумкин)"
        )
    else:
        await message.answer("🚫 Бу бўлим фақат бот эгаси учун!")

@dp.message(F.text == "🍴 Меню")
async def show_menu(message: types.Message):
    await message.answer("Меню тез орада тўлиқ ишлайди. Ҳозирча тест режимида.")

@dp.message(F.text == "📞 Алоқа")
async def contact(message: types.Message):
    await message.answer("👨‍💻 Админ: @TheCheffAdmin\n📞 Тел: +998 91 404 15 15")

@dp.message(F.text == "⬅️ Ортга")
async def go_back(message: types.Message):
    await message.answer("Бош меню", reply_markup=main_menu_kb(message.from_user.id))

# 5. АСОСИЙ ИШГА ТУШИРИШ
async def main():
    # Вeб-сeрвeр ва ботни бир вақтда ишга тушириш
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Бот тўхтатилди!")
