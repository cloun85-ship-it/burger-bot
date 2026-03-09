# --- БУЮРТМА ВА ИХТИЁРИЙ ЛОКАЦИЯ (АДМИНГА ТЎЛОВ ТУРИ БИЛАН) ---

@dp.message(OrderStates.waiting_for_location)
async def process_location(message: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = message.from_user.id
    cart = user_carts.get(uid, [])
    
    # Локация маълумотини сақлаб қўямиз
    location_data = None
    if message.location:
        location_data = {"lat": message.location.latitude, "lon": message.location.longitude}
    
    # Буюртма маҳсулотларини матн кўринишига келтирамиз
    items_txt = ""
    total = 0
    for p in cart:
        sub = p['price'] * p['qty']
        total += sub
        items_txt += f"- {p['name']} x {p['qty']} = {sub:,} сўм\n"
    
    # Маълумотларни вақтинча сақлаймиз (тўлов турини кутамиз)
    await state.update_data(
        order_items=items_txt, 
        total_sum=total, 
        loc=location_data,
        customer_name=message.from_user.full_name
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Карта орқали", callback_data="pay_card")
    builder.button(text="💵 Нақд пулда", callback_data="pay_cash")
    builder.adjust(2)
    
    await message.answer("Раҳмат! Энди тўлов турини танланг:", reply_markup=builder.as_markup())

# --- ТЎЛОВ ТУРИНИ ҚАБУЛ ҚИЛИШ ВА АДМИНГА ЮБОРИШ ---

@dp.callback_query(F.data.startswith("pay_"))
async def finalize_order(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    uid = callback.from_user.id
    pay_type = "💳 Карта орқали" if callback.data == "pay_card" else "💵 Нақд пул"
    
    # Админга борадиган якуний чек
    order_report = (
        f"🔔 **ЯНГИ БУЮРТМА!**\n"
        f"👤 Мижоз: {data['customer_name']}\n"
        f"📞 Тел: {data['phone']}\n"
        f"💰 Тўлов шакли: **{pay_type}**\n\n"
        f"📦 Маҳсулотлар:\n{data['order_items']}\n"
        f"💵 **Жами: {data['total_sum']:,} сўм**"
    )

    # Админга юбориш
    await bot.send_message(ADMIN_ID, order_report)
    
    # Агар локация бўлса, уни ҳам юбориш
    if data.get('loc'):
        await bot.send_location(ADMIN_ID, data['loc']['lat'], data['loc']['lon'])
    else:
        await bot.send_message(ADMIN_ID, "📍 Локация юборилмади.")

    # Мижозга тасдиқнома
    confirm_msg = "✅ Буюртмангиз қабул қилинди!"
    if callback.data == "pay_card":
        confirm_msg += "\n\n💳 Картага ўтказма учун: `8600000000000000` (The Cheff Burger)"
    
    await callback.message.edit_text(confirm_msg)
    await callback.message.answer("Бош меню", reply_markup=main_menu(uid))
    
    # Саватчани тозалаш ва ҳолатни ёпиш
    user_carts[uid] = []
    await state.clear()
    await callback.answer()
