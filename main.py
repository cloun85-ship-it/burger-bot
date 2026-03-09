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

# МАҲСУЛОТЛАР (Бошланғич рўйхат)
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
    waiting_for_payment = State()

class AdminStates(StatesGroup):
    waiting_for_add_data = State()
    waiting_for_edit_price = State()

# 2. RENDER УЧУН ВЕБ-СЕРВЕР
async def handle(request):
    return web.Response(text="TheCheffBurger Bot is Active")

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
    builder.row(types.KeyboardButton(text="➕ Қўшиш"), types.KeyboardButton(text="📝 Таҳрирлаш"))
    builder.row(types.KeyboardButton(text="🗑 Ўчириш"), types.KeyboardButton(text="⬅️ Ортга"))
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

# --- БУЮРТМА ВА ЯКУНИЙ МEНЮГА ҚАЙТИШ ---
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
    await message.answer("Манзилни юборинг ёки ўтказиб юборинг:", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(OrderStates.waiting_for_location)

@dp.message(OrderStates.waiting_for_location)
async def process_location(message: types.Message, state: FSMContext):
    loc = {"lat": message.location.latitude, "lon": message.location.longitude} if message.location else None
    await state.update_data(location=loc)
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Карта орқали", callback_data="pay_card")
    builder.button(text="💵 Нақд пулда", callback_data="pay_cash")
    await message.answer("Тўлов турини танланг:", reply_markup=builder.as_markup())
    await state.set_state(OrderStates.waiting_for_payment)

@dp.callback_query(OrderStates.waiting_for_payment, F.data.startswith("pay_"))
async def finalize_order(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    uid = callback.from_user.id
    pay_type = "💳 Карта" if callback.data == "pay_card" else "💵 Нақд пул"
    cart = user_carts.get(uid, [])
    
    order_txt = f"🔔 **ЯНГИ БУЮРТМА!**\n👤 {callback.from_user.full_name}\n📞 {data['phone']}\n💰 Тўлов: {pay_type}\n\n"
    total = 0
    for p in cart:
        sub = p['price'] * p['qty']
        total += sub
        order_txt += f"- {p['name']} x {p['qty']} = {sub:,}\n"
    order_txt += f"\n💰 Жами: {total:,} сўм"

    await bot.send_message(ADMIN_ID, order_txt)
    if data.get('location'):
        await bot.send_location(ADMIN_ID, data['location']['lat'], data['location']['lon'])
    
    await callback.message.delete()
    await callback.message.answer(f"✅ Раҳмат! Буюртмангиз қабул қилинди.\nТўлов шакли: {pay_type}\n\nЯна буюртма беришингиз мумкин 👇", reply_markup=main_menu(uid))
    user_carts[uid] = []
    await state.clear()

# --- АДМИН ПАНEЛИ (ҲАММА ТУГМАЛАР ТЎЛИҚ ИШЛАЙДИ) ---
@dp.message(F.text == "⚙️ Админ Панель")
async def admin_main(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 Админ бошқаруви:", reply_markup=admin_kb())

@dp.message(F.text == "➕ Қўшиш")
async def admin_add_start(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Маҳсулотни `Номи - Нархи` кўринишида юборинг:\nМисол: `Биг Мак - 45000`")
        await state.set_state(AdminStates.waiting_for_add_data)

@dp.message(AdminStates.waiting_for_add_data)
async def process_admin_add(message: types.Message, state: FSMContext):
    try:
        name, price = message.text.split("-")
        MENU[name.strip()] = int(price.strip())
        await message.answer(f"✅ Қўшилди: {name.strip()}", reply_markup=admin_kb())
        await state.clear()
    except:
        await message.answer("❌ Хато! Формат: `Номи - Нархи` (масалан: Лаваш - 25000)")

@dp.message(F.text == "📝 Таҳрирлаш")
async def admin_edit_list(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        builder = InlineKeyboardBuilder()
        for item in MENU.keys():
            builder.button(text=f"⚙️ {item}", callback_data=f"edit_{item}")
        builder.adjust(1)
        await message.answer("Нархини ўзгартириш учун танланг:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("edit_"))
async def process_edit_start(callback: types.CallbackQuery, state: FSMContext):
    item = callback.data.split("_")[1]
    await state.update_data(edit_item=item)
    await callback.message.answer(f"💰 {item} учун янги нархни ёзинг:")
    await state.set_state(AdminStates.waiting_for_edit_price)
    await callback.answer()

@dp.message(AdminStates.waiting_for_edit_price)
async def process_edit_price(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        data = await state.get_data()
        item = data['edit_item']
        MENU[item] = int(message.text)
        await message.answer(f"✅ {item} нархи {message.text} сўмга ўзгарди.", reply_markup=admin_kb())
        await state.clear()
    else:
        await message.answer("Фақат рақам ёзинг!")

@dp.message(F.text == "🗑 Ўчириш")
async def admin_del_list(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        builder = InlineKeyboardBuilder()
        for item in MENU.keys():
            builder.button(text=f"❌ {item}", callback_data=f"del_{item}")
        builder.adjust(1)
        await message.answer("Ўчириш учун танланг:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("del_"))
async def process_admin_del(callback: types.CallbackQuery):
    item = callback.data.split("_")[1]
    if item in MENU: del MENU[item]
    await callback.message.edit_text(f"✅ {item} ўчирилди."); await callback.answer()

@dp.message(F.text == "📞 Алоқа")
async def contact_info(message: types.Message):
    await message.answer("👨‍💻 Админ: @TheCheffAdmin\n📞 Тел: +998 91 404 15 15")

@dp.message(F.text == "⬅️ Ортга")
async def go_back(message: types.Message):
    await message.answer("Бош меню", reply_markup=main_menu(message.from_user.id))

@dp.callback_query(F.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    user_carts[callback.from_user.id] = []
    await callback.message.edit_text("🛒 Саватча тозаланди."); await callback.answer()

async def main():
    await asyncio.gather(start_web_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
