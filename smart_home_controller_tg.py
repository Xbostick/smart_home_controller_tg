import os
import logging
import subprocess
from telegram import Update, InlineKeyboardButton, KeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler
from wakeonlan import send_magic_packet
from yeelight import Bulb

from smart_home_controller_support import get_secure_data, get_local_data, LOCAL_SERVING, Authorized_Only, Admin_Only, update_verified_list_file, update_admins_list_file

str_to_greet_newcomers1 = "Hello! I'm a telegram bot for remote controll your smart home devices for 196. \n"
str_to_greet_newcomers2 = "To get started, you need to be confirmed by admins. W8 please, they already notificated. \n"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

ADMINS, API_TOKEN, VALDATED_USERS = get_secure_data()
LOCALS = get_local_data()

async def verify_notification(update, context):
    await context.bot.sendMessage(chat_id=update.effective_chat.id, text="W8 for admin verifing")
    for admin in ADMINS.values():
        print(admin)
        print(admin.keys())
        notification = f"User {update.message.chat.username} want to have controls. Is it fine to you?\n \
type in \"/verify username\" to confirm"
        await context.bot.sendMessage(chat_id=admin["id"], text=notification)


async def start(update, context):
    """Function to handle the /start command

    Args:
        update (_type_): _description_
        context (_type_): _description_
    """
    await context.bot.send_message(chat_id=update.effective_chat.id, text=str_to_greet_newcomers1)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=str_to_greet_newcomers2)
    
    if update.message.chat.username not in ADMINS and update.message.chat.username not in VALDATED_USERS:
            await verify_notification(update, context)
    elif update.message.chat.username in VALDATED_USERS:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are in validated users list. Nice to meet you! Dialog id saved")
        if not VALDATED_USERS[update.message.chat.username]["id"]:
            VALDATED_USERS[update.message.chat.username]["id"] = update.message.chat.id
            update_verified_list_file(VALDATED_USERS)            
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are in admin list. Nice to meet you! Dialog id saved")
        print(f"added Admin name = {update.message.chat.username}, id = {update.message.chat.id} \n")
        ADMINS[update.message.chat.username] = {"id" : update.message.chat.id,
                                               "actions" : None}
        update_admins_list_file(ADMINS)
        print(f"New admn list = {ADMINS}")

@Admin_Only
async def verify(update, context):
    """Functiom to handle the /verify command

    Args:
        update (_type_): _description_
        context (_type_): _description_
    """
    if not len(context.args):
        update.message.reply_text("Please specify the username of the user you want to verify")
        return

    username = context.args[0]
    chat_id_user = context.args[1]
    if username[0] == "@":
        username = username[1:]

    VALDATED_USERS[username] = {"id" : chat_id_user,
                                "actions" : None}
    with open("./session_data.txt","a") as f:
      await f.write(f"\n{username} {chat_id_user}")
      f.close()
    await context.bot.send_message(chat_id=chat_id_user, text= f"You are verified")
    await context.bot.send_message(chat_id=update.effective_chat.id, text= f"{username} is verified")

@Authorized_Only    
async def WakeUpNeo(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text= f"WakeUp Package sent")
    send_magic_packet("7C,10,C9,43,17,E3")

def build_menu(buttons, n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu

async def menu_debug(update, context):
   return  "bulbs"
async def end(update, context):
    return  ConversationHandler.END


if __name__ == '__main__':
    subprocess.Popen(['python3', str(os.path.join(ROOT_DIR,"auto_light_up.py"))])
    print(f"TOKKEN = {API_TOKEN}\n\
          ADMINS = {ADMINS}\n \
          VALDATED_USERS = {VALDATED_USERS}")
    application = ApplicationBuilder().token(API_TOKEN[:-1]).build()

    
    start_handler = CommandHandler('start', start)
    verify_handler = CommandHandler('verify', verify)
    WakeUpNeo_handler = CommandHandler('wakeup', WakeUpNeo)
    # Debug_handler = CommandHandler('debug', menu_debug)

    application.add_handler(start_handler)
    application.add_handler(verify_handler)
    application.add_handler(WakeUpNeo_handler)
    # application.add_handler(Debug_handler)

    local_handlers = []
    for obj in LOCAL_SERVING:
        local_handlers.append(CommandHandler(
            obj, 
            LOCAL_SERVING[obj]["processing"]
            ))

    conv_handler = ConversationHandler(
        entry_points=local_handlers,
        states={
            obj : [CallbackQueryHandler(LOCAL_SERVING[obj]["callback"])] for obj in LOCAL_SERVING
        },
        fallbacks=[CallbackQueryHandler(LOCAL_SERVING[obj]["callback"]) for obj in LOCAL_SERVING],
    )

    application.add_handler(conv_handler)

    application.run_polling()

