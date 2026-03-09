import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# 1. СОЗЛАМАЛАР
API_TOKEN = '8614302276:AAHzG09FGl-4R5r4_4VNSfOD0Oemhlshfbs'
ADMIN_ID = 58170268 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# МАҲСУЛОТЛАР (База ўрнида вақтинчалик луғат)
MENU = {
    "🍔 Чизбургер": 35000,
    "🍔 Гамбургер": 30000,
    "🍟 Фри": 15000
}

# АДМИН УЧУН ҲОЛАТЛАР (State)
class AdminStates(StatesGroup):
    waiting_for_item_data = State()

# 2. RENDER ВЕБ-СЕРВЕРИ
async def handle(request):
    return web.Response(text="Бот ишлаяпти!")

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
    builder.row(types.KeyboardButton(text="📞 Алоқа"))
    if uid == ADMIN_ID:
        builder.row(types.KeyboardButton(text="⚙️ Админ Панель"))
    return builder.as_markup(resize_keyboard=True)

def admin_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="➕ Қўшиш"), types.KeyboardButton(text="🗑 Ўчириш"))
    builder.row(types.KeyboardButton(text="⬅️ Ортга"))
    return builder.as_markup(resize_keyboard=True)

# 4. БОТ МАНТИҚИ
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🍔 **The Cheff Burger**-га хуш келибсиз!", reply_markup=main_menu(message.from_user.id))

# --- ФОЙДАЛАНУВЧИ БЎЛИМИ ---
@dp.message(F.text == "🍴 Меню")
async def show_menu(message: types.Message):
    if not MENU:
        await message.answer("Меню ҳозирча бўш.")
        return
    
    text = "🍴 **Бизнинг меню:**\n\n"
    builder = InlineKeyboardBuilder()
    for item, price in MENU.items():
        text += f"🔹 {item} — {price:,} сўм\n"
        builder.button(text=f"🛒 {item}", callback_data=f"order_{item}")
    builder.adjust(2)
    await message.answer(text, reply_markup=builder.as_markup())

@dp.message(F.text == "📞 Алоқа")
async def contact(message: types.Message):
    await message.answer("👨‍💻 Админ: @TheCheffAdmin\n📞 Тел: +998 91 404 15 15")

# --- АДМИН ПАНЕЛИ (ТЎЛИҚ ИШЛАЙДИГАН) ---
@dp.message(F.text == "⚙️ Админ Панель")
async def admin_main(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 **Админ бошқаруви:**", reply_markup=admin_kb())

@dp.message(F.text == "➕ Қўшиш")
async def add_item(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Янги маҳсулотни мана бундай юборинг:\n\n`Номи - Нархи` \n\n*Мисол: Лаваш - 28000*")
        await state.set_state(AdminStates.waiting_for_item_data)

@dp.message(AdminStates.waiting_for_item_data)
async def process_adding(message: types.Message, state: FSMContext):
    try:
        name, price = message.text.split("-")
        MENU[name.strip()] = int(price.strip())
        await message.answer(f"✅ Тайёр! Менюга қўшилди: **{name.strip()}**", reply_markup=admin_kb())
        await state.clear()
    except:
        await message.answer("❌ Хато! Форматни текшириб қайтадан ёзинг (Номи - Нархи).")

@dp.message(F.text == "🗑 Ўчириш")
async def delete_list(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        builder = InlineKeyboardBuilder()
        for item in MENU.keys():
            builder.button(text=f"❌ {item}", callback_data=f"del_{item}")
        builder.adjust(1)
        await message.answer("Ўчириш учун танланг:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("del_"))
async def del_item(callback: types.CallbackQuery):
    item = callback.data.split("_")[1]
    if item in MENU:
        del MENU[item]
        await callback.message.edit_text(f"✅ {item} ўчирилди!")
    await callback.answer()

@dp.message(F.text == "⬅️ Ортга")
async def go_back(message: types.Message):
    await message.answer("Бош меню", reply_markup=main_menu(message.from_user.id))

# 5. ИШГА ТУШИРИШ
async def main():
    await asyncio.gather(start_web_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
