import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# 1. СОЗЛАМАЛАР
API_TOKEN = '8614302276:AAHzG09FGl-4R5r4_4VNSfOD0Oemhlshfbs'
ADMIN_ID = 58170268

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# МАЪЛУМОТЛАР ОМБОРИ (Вақтинчалик - базага улагунча)
# Маҳсулотлар: "номи": нархи
MENU = {
    "🍔 Чизбургер": 35000,
    "🍔 Гамбургер": 30000,
    "🥤 Pepsi 1.5L": 15000,
    "🍟 Фри": 15000
}

# 2. RENDER УЧУН ВEБ СEРВEР
async def handle(request):
    return web.Response(text="TheCheffBurger Bot Live Status: OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# 3. КЛАВИАТУРАЛАР
def main_menu(uid):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🍴 Меню"))
    builder.row(types.KeyboardButton(text="🛒 Саватча"), types.KeyboardButton(text="📞 Алоқа"))
    if uid == ADMIN_ID:
        builder.row(types.KeyboardButton(text="⚙️ Админ Панель"))
    return builder.as_markup(resize_keyboard=True)

def admin_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="➕ Маҳсулот қўшиш"), types.KeyboardButton(text="🗑 Маҳсулот ўчириш"))
    builder.row(types.KeyboardButton(text="📊 Статистика"), types.KeyboardButton(text="⬅️ Ортга"))
    return builder.as_markup(resize_keyboard=True)

# 4. БОТ ФУНКЦИЯЛАРИ (ХEНДЛEРЛАР)
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("🍔 **The Cheff Burger**-га хуш келибсиз!", reply_markup=main_menu(message.from_user.id))

# --- АДМИН ПАНEЛИ ҚИСМИ ---
@dp.message(F.text == "⚙️ Админ Панель")
async def show_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 **Админ Бошқарув Панели:**", reply_markup=admin_kb())
    else:
        await message.answer("🚫 Рухсат берилмаган.")

@dp.message(F.text == "➕ Маҳсулот қўшиш")
async def add_item_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Янги маҳсулотни мана бу форматда юборинг:\n\n`Номи - Нархи` (масалан: HotDog - 20000)")

@dp.message(lambda m: " - " in m.text and m.from_user.id == ADMIN_ID)
async def process_add_item(message: types.Message):
    try:
        name, price = message.text.split(" - ")
        MENU[name.strip()] = int(price.strip())
        await message.answer(f"✅ Маҳсулот қўшилди: {name}")
    except:
        await message.answer("❌ Хато! Форматни текширинг.")

@dp.message(F.text == "🗑 Маҳсулот ўчириш")
async def delete_item_list(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        builder = InlineKeyboardBuilder()
        for item in MENU.keys():
            builder.button(text=f"❌ {item}", callback_data=f"del_{item}")
        builder.adjust(1)
        await message.answer("Ўчириш учун маҳсулотни танланг:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("del_"))
async def process_delete(callback: types.CallbackQuery):
    item_name = callback.data.split("_")[1]
    if item_name in MENU:
        del MENU[item_name]
        await callback.answer(f"{item_name} ўчирилди")
        await callback.message.edit_text(f"✅ {item_name} менюдан олиб ташланди.")

# --- ФОЙДАЛАНУВЧИ МEНЮСИ ---
@dp.message(F.text == "🍴 Меню")
async def user_menu(message: types.Message):
    res = "🍴 **Бизнинг меню:**\n\n"
    builder = InlineKeyboardBuilder()
    for item, price in MENU.items():
        res += f"🔸 {item} — {price:,} сўм\n"
        builder.button(text=f"🛒 {item}", callback_data=f"buy_{item}")
    builder.adjust(2)
    await message.answer(res, reply_markup=builder.as_markup())

@dp.message(F.text == "📞 Алоқа")
async def contact(message: types.Message):
    await message.answer("👨‍💻 Админ: @TheCheffAdmin\n📞 Тел: +998 91 404 15 15")

@dp.message(F.text == "⬅️ Ортга")
async def back_to_main(message: types.Message):
    await message.answer("Бош меню", reply_markup=main_menu(message.from_user.id))

# 5. ИШГА ТУШИРИШ
async def main():
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
