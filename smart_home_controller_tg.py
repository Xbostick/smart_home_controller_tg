import os
import logging
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from wakeonlan import send_magic_packet

def Authorized_Only(func):
    async def wrapper(update: Update, context: ContextTypes, *args, **kwargs):
        print(update.message.chat.username)
        if update.message.chat.username in VALDATED_USERS.keys() or update.message.chat.username in ADMINS.keys():
            return await func(update, context, *args, **kwargs)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to use this bot.")
    return wrapper

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

str_to_greet_newcomers1 = "Hello! I'm a telegram bot for remote controll your smart home devices for 196. \n"
str_to_greet_newcomers2 = "To get started, you need to be confirmed by admins. W8 please, they already notificated. \n"

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(ROOT_DIR, "secure_data.txt"), "r",encoding='ASCII') as f:
    """This file contains  Telegram API_TOKEN and ADMINS. So init it
    """
    API_TOKEN = f.readline().split(' ')[1]
    ADMINS = {admin : {} for admin in f.readline().split(' ')[1:] }
print (ADMINS, API_TOKEN)
if os.path.exists(os.path.join(ROOT_DIR,"session_data.txt")):
    with open (os.path.join(ROOT_DIR,"session_data.txt"), "r") as f:
        VALDATED_USERS = {line.split(' ')[0] : line.split(' ')[1] for line in f.readlines()}
else:
    VALDATED_USERS = {}


async def verify_notification(update, context):
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
    ##await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")
    await context.bot.send_message(chat_id=update.effective_chat.id, text=str_to_greet_newcomers1)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=str_to_greet_newcomers2)
    if update.message.chat.username not in ADMINS and update.message.chat.username not in VALDATED_USERS:
            await verify_notification(update, context)
    elif update.message.chat.username in VALDATED_USERS:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are in validated users list. Nice to meet you! Dialog id saved")
        if not VALDATED_USERS[update.message.chat.username]["id"]:
            VALDATED_USERS[update.message.chat.username]["id"] = update.message.chat.id            
            with open("session_data.txt", "a+", encoding='ASCII') as f:
                f.write(f"{update.message.chat.username} {update.message.chat.id}\n")   
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are in admin list. Nice to meet you! Dialog id saved")
        print(f"added Admin name = {update.message.chat.username}, id = {update.message.chat.id} \n")
        ADMINS[update.message.chat.username] = {"id" : update.message.chat.id,
                                               "actions" : None}
        print(f"New admn list = {ADMINS}")


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
    if username[0] == "@":
        username = username[1:]

    VALDATED_USERS[username] = {"id" : None,
                                "actions" : None}
    await context.bot.send_message(chat_id=update.effective_chat.id, text= f"{username} is verified")

@Authorized_Only    
async def WakeUpNeo(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text= f"WakeUp Package sent")
    send_magic_packet("7C,10,C9,43,17,E3")

if __name__ == '__main__':
    subprocess.Popen(['python3', str(os.path.join(ROOT_DIR,"auto_light_up.py"))])
    print(f"TOKKEN = {API_TOKEN}\n\
          ADMINS = {ADMINS}\n \
          VALDATED_USERS = {VALDATED_USERS}")
    application = ApplicationBuilder().token(API_TOKEN[:-1]).build()

    
    start_handler = CommandHandler('start', start)
    verify_handler = CommandHandler('verify', verify)
    WakeUpNeo_handler = CommandHandler('wakeup', WakeUpNeo)

    application.add_handler(start_handler)
    application.add_handler(verify_handler)
    application.add_handler(WakeUpNeo_handler)
    
    application.run_polling()

