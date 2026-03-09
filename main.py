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

# МАҲСУЛОТЛАР ВА САВАТЧА
MENU = {
    "🍔 Чизбургер": 35000,
    "🍔 Гамбургер": 30000,
    "🍟 Фри": 15000,
    "🥤 Pepsi 1.5L": 15000
}
user_carts = {} # {user_id: [маҳсулотлар]}

class AdminStates(StatesGroup):
    waiting_for_item_data = State()

# 2. RENDER ВEБ-СEРВEРИ
async def handle(request):
    return web.Response(text="TheCheffBurger Bot: Active")

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

# 4. БОТ МАНТИҚИ
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    if uid not in user_carts:
        user_carts[uid] = []
    await message.answer("🍔 **The Cheff Burger**-га хуш келибсиз!", reply_markup=main_menu(uid))

# --- МEНЮ ВА САВАТЧАГА ҚЎШИШ ---
@dp.message(F.text == "🍴 Меню")
async def show_menu(message: types.Message):
    text = "🍴 **Бизнинг меню:**\n\nМаҳсулотни танланг:"
    builder = InlineKeyboardBuilder()
    for item, price in MENU.items():
        builder.button(text=f"{item} ({price:,} сўм)", callback_data=f"buy_{item}")
    builder.adjust(1)
    await message.answer(text, reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def add_to_cart(callback: types.CallbackQuery):
    item = callback.data.split("_")[1]
    uid = callback.from_user.id
    if uid not in user_carts: user_carts[uid] = []
    user_carts[uid].append(item)
    await callback.answer(f"✅ {item} саватчага қўшилди!")

# --- САВАТЧАНИ КЎРИШ ВА БУЮРТМА БEРИШ ---
@dp.message(F.text == "🛒 Саватча")
async def view_cart(message: types.Message):
    uid = message.from_user.id
    cart = user_carts.get(uid, [])
    if not cart:
        await message.answer("🛒 Саватчангиз ҳозирча бўш.")
        return

    summary = "🛒 **Сизнинг саватчангиз:**\n\n"
    total = 0
    for item in set(cart):
        count = cart.count(item)
        price = MENU[item] * count
        total += price
        summary += f"🔸 {item} x {count} = {price:,} сўм\n"
    
    summary += f"\n💰 **Жами:** {total:,} сўм"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Буюртмани тасдиқлаш", callback_data="confirm_order")
    builder.button(text="🗑 Тозалаш", callback_data="clear_cart")
    builder.adjust(1)
    
    await message.answer(summary, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "confirm_order")
async def confirm_order(callback: types.CallbackQuery):
    uid = callback.from_user.id
    cart = user_carts.get(uid, [])
    if not cart: return

    # Админга хабар юбориш
    order_text = f"🔔 **ЯНГИ БУЮРТМА!**\n\n👤 Мижоз: {callback.from_user.full_name}\n🆔 ID: `{uid}`\n\n**Маҳсулотлар:**\n"
    for item in set(cart):
        order_text += f"- {item} x {cart.count(item)}\n"
    
    await bot.send_message(ADMIN_ID, order_text)
    user_carts[uid] = [] # Саватчани бўшатиш
    await callback.message.edit_text("✅ Буюртмангиз қабул қилинди! Тез орада боғланамиз.")
    await callback.answer()

@dp.callback_query(F.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    user_carts[callback.from_user.id] = []
    await callback.message.edit_text("🛒 Саватча тозаланди.")
    await callback.answer()

# --- АДМИН ПАНEЛИ ---
@dp.message(F.text == "⚙️ Админ Панель")
async def admin_main(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        builder = ReplyKeyboardBuilder()
        builder.row(types.KeyboardButton(text="➕ Қўшиш"), types.KeyboardButton(text="🗑 Ўчириш"))
        builder.row(types.KeyboardButton(text="⬅️ Ортга"))
        await message.answer("🛠 **Админ бошқаруви:**", reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.text == "➕ Қўшиш")
async def add_item(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Формат: `Номи - Нархи` (масалан: Лаваш - 28000)")
        await state.set_state(AdminStates.waiting_for_item_data)

@dp.message(AdminStates.waiting_for_item_data)
async def process_adding(message: types.Message, state: FSMContext):
    try:
        name, price = message.text.split("-")
        MENU[name.strip()] = int(price.strip())
        await message.answer(f"✅ Қўшилди: {name.strip()}")
        await state.clear()
    except:
        await message.answer("❌ Хато! Қайтадан ёзинг.")

@dp.message(F.text == "📞 Алоқа")
async def contact(message: types.Message):
    await message.answer("👨‍💻 Админ: @TheCheffAdmin\n📞 Тел: +998 91 404 15 15")

@dp.message(F.text == "⬅️ Ортга")
async def go_back(message: types.Message):
    await message.answer("Бош меню", reply_markup=main_menu(message.from_user.id))

# 5. ИШГА ТУШИРИШ
async def main():
    await asyncio.gather(start_web_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
