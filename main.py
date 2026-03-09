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
PAYMENT_TOKEN = '398062629:TEST:999999999_F9C8' # Тест режими учун (Click/Payme токенини қўйишингиз мумкин)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

MENU = {
    "🍔 Чизбургер": 35000,
    "🍔 Гамбургер": 30000,
    "🍟 Фри": 15000,
    "🥤 Pepsi 1.5L": 15000
}
user_carts = {}

class OrderStates(StatesGroup):
    waiting_for_qty = State()
    waiting_for_contact = State()
    waiting_for_location = State()

class AdminStates(StatesGroup):
    waiting_for_item_data = State()

# 2. RENDER УЧУН "WAKE UP" ВЕБ-СЕРВЕРИ (Бот ўчиб қолмаслиги учун)
async def handle(request):
    return web.Response(text="Bot is running!")

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
    user_carts[message.from_user.id] = []
    await message.answer("🍔 **The Cheff Burger**-га хуш келибсиз!", reply_markup=main_menu(message.from_user.id))

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
    if not message.text.isdigit(): return
    
    qty = int(message.text)
    data = await state.get_data()
    item = data['chosen_item']
    uid = message.from_user.id
    if uid not in user_carts: user_carts[uid] = []
    user_carts[uid].append({"name": item, "price": MENU[item], "qty": qty})
    await state.clear()
    await message.answer(f"✅ {item} x {qty} саватчага қўшилди!", reply_markup=main_menu(uid))

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

# --- БУЮРТМА ВА ИХТИЁРИЙ ЛОКАЦИЯ ---
@dp.callback_query(F.data == "start_order")
async def start_order(callback: types.CallbackQuery, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📱 Телефон юбориш", request_contact=True))
    await callback.message.answer("Телефон рақамингизни юборинг:", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(OrderStates.waiting_for_contact)
    await callback.answer()

@dp.message(OrderStates.waiting_for_contact, F.contact)
async def process_contact(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📍 Локация юбориш", request_location=True))
    builder.row(types.KeyboardButton(text="⏭ Ўтказиб юбориш"))
    await message.answer("Етказиб бериш манзилини (локация) юборинг ёки ўтказиб юборинг:", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(OrderStates.waiting_for_location)

@dp.message(OrderStates.waiting_for_location)
async def process_location(message: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = message.from_user.id
    cart = user_carts.get(uid, [])
    
    order_txt = f"🔔 **ЯНГИ БУЮРТМА!**\n👤 {message.from_user.full_name}\n📞 {data['phone']}\n\n"
    total = 0
    for p in cart:
        sub = p['price'] * p['qty']
        total += sub
        order_txt += f"- {p['name']} x {p['qty']}\n"
    order_txt += f"\n💰 Жами: {total:,} сўм"

    # Админга буюртма юбориш
    await bot.send_message(ADMIN_ID, order_txt)
    if message.location:
        await bot.send_location(ADMIN_ID, message.location.latitude, message.location.longitude)
    else:
        await bot.send_message(ADMIN_ID, "📍 Локация юборилмади.")

    # Тўлов қилиш тугмаси (Мисол тариқасида)
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Click орқали тўлаш", callback_data="pay_click")
    builder.button(text="💵 Нақд пулда", callback_data="pay_cash")
    
    await message.answer("Раҳмат! Буюртма қабул қилинди. Тўлов турини танланг:", reply_markup=builder.as_markup(), reply_markup=main_menu(uid))
    user_carts[uid] = []
    await state.clear()

@dp.callback_query(F.data == "pay_click")
async def pay_click(callback: types.CallbackQuery):
    await callback.message.answer("💳 Click орқали тўлов учун: +998 91 404 15 15 рақамига картага ўтказинг ва чекини юборинг.")
    await callback.answer()

@dp.callback_query(F.data == "pay_cash")
async def pay_cash(callback: types.CallbackQuery):
    await callback.message.answer("💵 Буюртмангиз қабул қилинди. Етказиб берилганда нақд тўлашингиз мумкин.")
    await callback.answer()

# --- АДМИН ПАНEЛИ ---
@dp.message(F.text == "⚙️ Админ Панель")
async def admin_main(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        builder = ReplyKeyboardBuilder()
        builder.row(types.KeyboardButton(text="➕ Қўшиш"), types.KeyboardButton(text="🗑 Ўчириш"))
        builder.row(types.KeyboardButton(text="⬅️ Ортга"))
        await message.answer("🛠 Админ бошқаруви:", reply_markup=builder.as_markup(resize_keyboard=True))

# 5. ИШГА ТУШИРИШ
async def main():
    await asyncio.gather(start_web_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
