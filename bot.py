import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from config import BOT_TOKEN

with open("fractions.json", "r", encoding="utf-8") as f:
    data = json.load(f)

with open("templates.json", "r", encoding="utf-8") as f:
    templates = json.load(f)

fractions = {f["code"]: f for f in data["fractions"]}
roles = {}
for group in data["admin_roles"].values():
    photo = group["photo_id"]
    for role_name in group["roles"]:
        roles[role_name] = {"title": role_name, "photo": photo}

CHOOSING_TYPE, CHOOSING_ACTION, CHOOSING_FACTION, CHOOSING_ROLE, TYPING, PROMO_REWARD, EVENT_INPUT, BLAT_DATE = range(8)
BLAT_STEP = range(1)
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Лидер", callback_data="type_leader"),
         InlineKeyboardButton("Заместитель", callback_data="type_deputy")],
        [InlineKeyboardButton("Администрация", callback_data="type_admin")],
        [InlineKeyboardButton("Промокод", callback_data="type_promo")],
        [InlineKeyboardButton("Мероприятия", callback_data="type_events")],
        [InlineKeyboardButton("День блата", callback_data="type_blat")]
    ]
    await update.message.reply_text("Выберите шаблон для поста:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSING_TYPE

async def debug_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Chat ID: {update.effective_chat.id}")

async def type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data_type = query.data.replace("type_", "")
    user_data[user_id] = {"type": data_type}

    if data_type in ["leader", "deputy", "admin"]:
        keyboard = [[
            InlineKeyboardButton("Назначен", callback_data="action_appointed"),
            InlineKeyboardButton("Снят", callback_data="action_removed")
        ]]
        await query.edit_message_text("Уточните действие:", reply_markup=InlineKeyboardMarkup(keyboard))
        return CHOOSING_ACTION
    elif data_type == "promo":
        await query.edit_message_text("Введите промокод:")
        return TYPING
    elif data_type == "events":
        context.user_data["events"] = []
        await query.edit_message_text("Вводите мероприятия в формате: \n• «Название» — в 00:00\nНапишите /готово для завершения.")
        return EVENT_INPUT
    elif data_type == "blat":
        keyboard = [
            [InlineKeyboardButton(f["display_name"], callback_data=f"blat_faction_{code}")]
            for code, f in fractions.items()
        ]
        await query.edit_message_text("Выберите фракцию для дня блата:", reply_markup=InlineKeyboardMarkup(keyboard))
        return BLAT_STEP

async def blat_faction_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    code = query.data.replace("blat_faction_", "")
    fraction = fractions.get(code)
    if not fraction:
        await query.edit_message_text("Фракция не найдена.")
        return ConversationHandler.END

    user_data[user_id] = {
        "type": "blat",
        "faction": fraction
    }

    keyboard = [
        [InlineKeyboardButton("Дата начала", callback_data="blat_start_date")],
        [InlineKeyboardButton("Время начала", callback_data="blat_start_time")],
        [InlineKeyboardButton("Дата окончания", callback_data="blat_end_date")],
        [InlineKeyboardButton("Время окончания", callback_data="blat_end_time")]
    ]
    await query.edit_message_text("Что укажем дальше?", reply_markup=InlineKeyboardMarkup(keyboard))
    return BLAT_STEP

async def blat_date_step_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    step = query.data
    current = user_data[user_id]
    current["blat_progress"] = step

    messages = {
        "blat_start_date": "Введите дату начала (ДД.ММ):",
        "blat_start_time": "Введите время начала (чч:мм):",
        "blat_end_date": "Введите дату окончания (ДД.ММ):",
        "blat_end_time": "Введите время окончания (чч:мм):"
    }

    await query.edit_message_text(messages[step])
    return BLAT_DATE

async def action_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    action = query.data.replace("action_", "")
    user_data[user_id]["action"] = action
    data_type = user_data[user_id]["type"]

    if data_type in ["leader", "deputy"]:
        buttons = [[InlineKeyboardButton(f["display_name"], callback_data=f"faction_{code}")] for code, f in fractions.items()]
        await query.edit_message_text("Выберите фракцию:", reply_markup=InlineKeyboardMarkup(buttons))
        return CHOOSING_FACTION
    elif data_type == "admin":
        buttons = [[InlineKeyboardButton(role, callback_data=f"role_{role}")] for role in roles.keys()]
        await query.edit_message_text("Выберите роль:", reply_markup=InlineKeyboardMarkup(buttons))
        return CHOOSING_ROLE

async def faction_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    code = query.data.replace("faction_", "")
    fraction = fractions.get(code)
    if not fraction:
        await query.edit_message_text("Фракция не найдена.")
        return ConversationHandler.END

    user_data[user_id]["faction"] = fraction
    await query.edit_message_text("Введите никнейм:")
    return TYPING

async def role_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    role_key = query.data.replace("role_", "")
    role = roles.get(role_key)
    if not role:
        await query.edit_message_text("Роль не найдена.")
        return ConversationHandler.END

    user_data[user_id]["role"] = role
    await query.edit_message_text("Введите никнейм:")
    return TYPING

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current = user_data.get(user_id, {})
    data_type = current.get("type")
    text = update.message.text

    if data_type == "promo":
        if "promo" not in current:
            current["promo"] = text
            await update.message.reply_text("Введите приз:")
            return PROMO_REWARD

    elif data_type == "blat":
        step = current.get("blat_progress")

        if step == "blat_start_date":
            current["start_date"] = text
        elif step == "blat_start_time":
            current["start_time"] = text
        elif step == "blat_end_date":
            current["end_date"] = text
        elif step == "blat_end_time":
            current["end_time"] = text

        current["blat_progress"] = None

        if all(k in current for k in ["start_date", "start_time", "end_date", "end_time"]):
            f = current["faction"]
            result = templates["blat_day"].format(
                fraction_display=f["display_name"],
                start_date=f"{current['start_date']} {current['start_time']}",
                end_date=f"{current['end_date']} {current['end_time']}"
            )
            await update.message.reply_photo(photo=data["special_posts"]["blat_day"]["photo_id"], caption=result, parse_mode="HTML")
            return ConversationHandler.END

        for s in ["start_date", "start_time", "end_date", "end_time"]:
            if s not in current:
                next_step = f"blat_{s}"
                current["blat_progress"] = next_step
                await update.message.reply_text({
                    "blat_start_date": "Введите дату начала (ДД.ММ):",
                    "blat_start_time": "Введите время начала (чч:мм):",
                    "blat_end_date": "Введите дату окончания (ДД.ММ):",
                    "blat_end_time": "Введите время окончания (чч:мм):"
                }[next_step])
                return BLAT_DATE

    elif data_type in ["leader", "deputy", "admin"]:
        action = current.get("action", "appointed")
        name = text

        if data_type == "leader":
            f = current["faction"]
            template_key = f"leader_{action}"
            text = templates[template_key].format(name=name, fraction_display=f["display_name"])
            await update.message.reply_photo(photo=f["leader_photo_id"], caption=text, parse_mode="HTML")

        elif data_type == "deputy":
            f = current["faction"]
            template_key = f"deputy_{action}"
            text = templates[template_key].format(name=name, deputy_title=f["deputy_title"], fraction_display=f["display_name"])
            await update.message.reply_photo(photo=f["deputy_photo_id"], caption=text, parse_mode="HTML")

        elif data_type == "admin":
            r = current["role"]
            template_key = f"admin_{action}"
            text = templates[template_key].format(name=name, admin_role=r["title"])
            await update.message.reply_photo(photo=r["photo"], caption=text, parse_mode="HTML")

        return ConversationHandler.END

async def promo_reward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current = user_data.get(user_id, {})
    reward = update.message.text
    text = templates["promo_post"].format(promo_code=current["promo"], reward=reward)
    await update.message.reply_text(text, parse_mode="HTML")
    return ConversationHandler.END

async def event_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "/готово":
        events = "\n".join(context.user_data["events"])
        message = templates["events_post"].format(event_list=events)
        photo_id = data["special_posts"]["events"]["photo_id"]
        await update.message.reply_photo(photo=photo_id, caption=message, parse_mode="HTML")
        return ConversationHandler.END
    else:
        context.user_data["events"].append(text)
        return EVENT_INPUT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

ALLOWED_CHAT_IDS = [-1002584840179, -1002853394429]

app = ApplicationBuilder().token(BOT_TOKEN).build()

async def ignore_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return  # просто молча игнорирует

app.add_handler(MessageHandler(~filters.Chat(chat_id=ALLOWED_CHAT_IDS), ignore_handler))
app.add_handler(CommandHandler("getid", debug_chat_id))

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("newpost", start)],
    states={
        CHOOSING_TYPE: [CallbackQueryHandler(type_chosen, pattern="^type_.*")],
        CHOOSING_ACTION: [CallbackQueryHandler(action_chosen, pattern="^action_.*")],
        CHOOSING_FACTION: [CallbackQueryHandler(faction_chosen, pattern="^faction_.*")],
        CHOOSING_ROLE: [CallbackQueryHandler(role_chosen, pattern="^role_.*")],
        TYPING: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)],
        PROMO_REWARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, promo_reward_handler)],
        EVENT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_input_handler)],
        BLAT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)],
        BLAT_STEP: [
            CallbackQueryHandler(blat_date_step_handler, pattern="^blat_(start|end)_(date|time)$"),
            CallbackQueryHandler(blat_faction_chosen, pattern="^blat_faction_.*")
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

app.add_handler(conv_handler)

if __name__ == "__main__":
    print("Бот запущен")
    app.run_polling()
