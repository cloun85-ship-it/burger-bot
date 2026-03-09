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

# МАҲСУЛОТЛАР ВА ВАҚТИНЧАЛИК МАЪЛУМОТЛАР
MENU = {
    "🍔 Чизбургер": 35000,
    "🍔 Гамбургер": 30000,
    "🍟 Фри": 15000,
    "🥤 Pepsi 1.5L": 15000
}
user_carts = {} # {user_id: [{"name": n, "price": p, "qty": q}]}

# ҲОЛАТЛАР (States)
class OrderStates(StatesGroup):
    waiting_for_qty = State()
    waiting_for_contact = State()
    waiting_for_location = State()

class AdminStates(StatesGroup):
    waiting_for_item_data = State()

# 2. RENDER ВЕБ-СЕРВЕРИ
async def handle(request):
    return web.Response(text="TheCheffBurger Bot: Ready")

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
    user_carts[uid] = []
    await message.answer("🍔 **The Cheff Burger**-га хуш келибсиз!", reply_markup=main_menu(uid))

# --- МЕНЮ ВА СОНИНИ ТАНЛАШ ---
@dp.message(F.text == "🍴 Меню")
async def show_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    for item, price in MENU.items():
        builder.button(text=f"{item} ({price:,})", callback_data=f"select_{item}")
    builder.adjust(1)
    await message.answer("Маҳсулот танланг:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("select_"))
async def select_item(callback: types.CallbackQuery, state: FSMContext):
    item = callback.data.split("_")[1]
    await state.update_data(chosen_item=item)
    
    builder = ReplyKeyboardBuilder()
    for i in range(1, 10): builder.add(types.KeyboardButton(text=str(i)))
    builder.row(types.KeyboardButton(text="⬅️ Ортга"))
    
    await callback.message.answer(f"🔢 {item} дан нечта керак?", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(OrderStates.waiting_for_qty)
    await callback.answer()

@dp.message(OrderStates.waiting_for_qty)
async def process_qty(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Ортга":
        await state.clear()
        await message.answer("Бош меню", reply_markup=main_menu(message.from_user.id))
        return
    
    if not message.text.isdigit():
        await message.answer("Илтимос, фақат рақам юборинг!")
        return

    qty = int(message.text)
    data = await state.get_data()
    item = data['chosen_item']
    uid = message.from_user.id
    
    if uid not in user_carts: user_carts[uid] = []
    user_carts[uid].append({"name": item, "price": MENU[item], "qty": qty})
    
    await state.clear()
    await message.answer(f"✅ {item} x {qty} саватчага қўшилди!", reply_markup=main_menu(uid))

# --- САВАТЧА ВА БУЮРТМА (ЛОКАЦИЯ ВА ТEЛEФОН) ---
@dp.message(F.text == "🛒 Саватча")
async def view_cart(message: types.Message):
    uid = message.from_user.id
    cart = user_carts.get(uid, [])
    if not cart:
        await message.answer("🛒 Саватчангиз бўш.")
        return

    summary = "🛒 **Саватчангиз:**\n\n"
    total = 0
    for i, p in enumerate(cart, 1):
        sub = p['price'] * p['qty']
        total += sub
        summary += f"{i}. {p['name']} x {p['qty']} = {sub:,} сўм\n"
    summary += f"\n💰 **Жами:** {total:,} сўм"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🚕 Буюртма бериш", callback_data="start_order")
    builder.button(text="🗑 Тозалаш", callback_data="clear_cart")
    await message.answer(summary, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "start_order")
async def start_order(callback: types.CallbackQuery, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📱 Телефон юбориш", request_contact=True))
    await callback.message.answer("Буюртма учун телефон рақамингизни юборинг:", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(OrderStates.waiting_for_contact)
    await callback.answer()

@dp.message(OrderStates.waiting_for_contact, F.contact)
async def process_contact(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📍 Локация юбориш", request_location=True))
    await message.answer("Энди етказиб бериш манзилини (локация) юборинг:", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(OrderStates.waiting_for_location)

@dp.message(OrderStates.waiting_for_location, F.location)
async def process_location(message: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = message.from_user.id
    cart = user_carts.get(uid, [])
    
    # Админга буюртмани шакллантириш
    order_txt = f"🔔 **ЯНГИ БУЮРТМА!**\n👤 {message.from_user.full_name}\n📞 {data['phone']}\n\n"
    total = 0
    for p in cart:
        sub = p['price'] * p['qty']
        total += sub
        order_txt += f"- {p['name']} x {p['qty']}\n"
    order_txt += f"\n💰 Жами: {total:,} сўм"

    # Админга юбориш
    await bot.send_message(ADMIN_ID, order_txt)
    await bot.send_location(ADMIN_ID, message.location.latitude, message.location.longitude)
    
    user_carts[uid] = []
    await state.clear()
    await message.answer("✅ Раҳмат! Буюртмангиз қабул қилинди.", reply_markup=main_menu(uid))

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
        await message.answer("🛠 Админ бошқаруви:", reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.text == "➕ Қўшиш")
async def add_item_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Формат: `Номи - Нархи` (Мисол: Лаваш - 28000)")
        await state.set_state(AdminStates.waiting_for_item_data)

@dp.message(AdminStates.waiting_for_item_data)
async def process_admin_add(message: types.Message, state: FSMContext):
    try:
        name, price = message.text.split("-")
        MENU[name.strip()] = int(price.strip())
        await message.answer(f"✅ Қўшилди: {name.strip()}", reply_markup=main_menu(ADMIN_ID))
        await state.clear()
    except:
        await message.answer("❌ Хато! Формат: Номи - Нархи")

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
