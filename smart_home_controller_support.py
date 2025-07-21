import os
from yeelight import Bulb, BulbException
from telegram import Update, InlineKeyboardButton, KeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from time import sleep
import asyncio

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def update_admins_list_file(ADMINS):
    id = "id"
    _, API_TOKEN, _ = get_secure_data()
    with open(os.path.join(ROOT_DIR, "secure_data.txt"), "w",encoding='ASCII') as f:
        f.write(f"API_KEY_CTR {API_TOKEN}")
        f.write("ADMINS\n")
        for admin in ADMINS:
            f.write(f"{admin} {ADMINS[admin][id]}\n")
        f.close()

def update_verified_list_file(VERIFIED):
    id = "id"
    with open(os.path.join(ROOT_DIR, "session_data.txt"), "w",encoding='ASCII') as f:
        for user in VERIFIED:
            f.write(f"{user} {VERIFIED[user][id]}")
        f.close()


def get_secure_data() -> list[dict]:
    with open(os.path.join(ROOT_DIR, "secure_data.txt"), "r",encoding='ASCII') as f:
        """This file contains  Telegram API_TOKEN and ADMINS. So init it
        """
        API_TOKEN = f.readline().split(' ')[1]
        _ = f.readline() # ADMINS
        ADMINS = {line.split(' ')[0] : {"id" : line.split(' ')[1]} for line in f.readlines()}
    
    print(ADMINS, API_TOKEN)

    if os.path.exists(os.path.join(ROOT_DIR,"session_data.txt")):
        with open (os.path.join(ROOT_DIR,"session_data.txt"), "r") as f:
            VALDATED_USERS = {line.split(' ')[0] : {"id" : line.split(' ')[1]} for line in f.readlines()}
    else:
        VALDATED_USERS = {}

    return [ADMINS, API_TOKEN, VALDATED_USERS]

def get_local_data() -> dict[dict]:
    if os.path.exists(os.path.join(ROOT_DIR,"local_data.txt")):
        with open (os.path.join(ROOT_DIR,"local_data.txt"), "r", encoding='UTF8') as f:
            raw_local_data = [line for line in f.readlines()]
    else:
        return None
    
    fields = {}
    for i, line in enumerate(raw_local_data):
        if line[0] == "!":
            fields[line[1:-1]] = {}
            for one in raw_local_data[i+1:]:
                if one[0] != "!":
                    fields[line[1:-1]][one.split(' ')[0]] = one.split(' ')[1][:-1]
                else:
                    break
            # fields[line[1:]] = {line.split(' ')[0] : line.split(' ')[1] for line in raw_local_data[i:] if line[0]!="!"}
    print(fields)
    return fields


LOCALS = get_local_data()
ADMINS, API_TOKEN, VALDATED_USERS = get_secure_data()

def Authorized_Only(func):
    async def wrapper(update: Update, context, *args, **kwargs):
        print(update.message.chat.username)
        ADMINS, _, VALDATED_USERS = get_secure_data()
        if update.message.chat.username in VALDATED_USERS.keys() or update.message.chat.username in ADMINS.keys():
            return await func(update, context, *args, **kwargs)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to use this bot.")
    return wrapper

def Admin_Only(func):
    async def wrapper(update: Update, context, *args, **kwargs):
        print(update.message.chat.username)
        ADMINS, _, _ = get_secure_data()
        if update.message.chat.username in ADMINS.keys():
            return await func(update, context, *args, **kwargs)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not admin to use this command.")
    return wrapper


def Can_be_cancelled(func):
    async def wrapper(update: Update, context, *args, **kwargs):
        query = update.callback_query
        if query.data != "None":
            return await func(update, context, *args, **kwargs)
        else:
            await query.delete_message()
            return  ConversationHandler.END
    return wrapper

#_______________cancel_local_________________#

def cancel_local():
    return  ConversationHandler.END
    

#_______________Bulbs sections _______________#
async def switch_bulb(ip):
    bulb = Bulb(ip)
    try:
        bulb.toggle()
    except BulbException:
        await asyncio.sleep(2)
        bulb.turn_on()
    if bulb.get_properties()["power"] == "on":
        return "включен"
    else: 
        return "выключен"

def get_state_bulb():
    states = []
    for bulb in LOCALS["bulbs"]:
        try:
            if Bulb(LOCALS["bulbs"][bulb]).get_properties()["power"] == "on":
                states.append("\U0001F4A1")
            else:
                states.append("\U0001F311")
        except BulbException:
            states.append("\U0001F6E0")


    return states

@Authorized_Only
async def bulb_buttons(update, context):
    # список кнопок
    keyboard = [
        [ 
            InlineKeyboardButton(bulb + ' ' + state , callback_data=bulb) for bulb, state in zip(LOCALS["bulbs"].keys(),get_state_bulb())

        ], 
        [InlineKeyboardButton("Отмена", callback_data="None")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Что будем переключать?', reply_markup=reply_markup)
    return "bulbs"

@Can_be_cancelled
async def bulb_handler(update, context):
    query = update.callback_query
    variant = query.data
    toggle_bulb = asyncio.create_task(switch_bulb(LOCALS["bulbs"][variant]))
    await toggle_bulb
    await query.edit_message_text(text=f"{variant} {toggle_bulb.result()}")
    return  ConversationHandler.END
#_______________Server sections _______________#

@Authorized_Only
async def server_buttons(update, context):
    # список кнопок
    print("here")
    keyboard = [
        [ 
            InlineKeyboardButton(one, callback_data=one) for one in LOCALS["servers"].keys()

        ],
        [InlineKeyboardButton("Отмена", callback_data="None")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Пожалуйста, выберите:', reply_markup=reply_markup)
    return "servers"
    
@Can_be_cancelled
async def server_handler(update, context):
    query = update.callback_query
    variant = query.data
    await query.edit_message_text(text=f"Выбранный вариант: {variant}, ничего не будет :( ")
    return ConversationHandler.END


#_______________Strip sections _______________#

@Authorized_Only
async def server_buttons(update, context):
    # список кнопок
    print("here")
    keyboard = [
        [ 
            InlineKeyboardButton(one, callback_data=one) for one in LOCALS["servers"].keys()

        ],
        [InlineKeyboardButton("Отмена", callback_data="None")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Пожалуйста, выберите:', reply_markup=reply_markup)
    return "servers"
    
@Can_be_cancelled
async def server_handler(update, context):
    query = update.callback_query
    variant = query.data
    await query.edit_message_text(text=f"Выбранный вариант: {variant}, ничего не будет :( ")
    return ConversationHandler.END


#_____________________end_____________________#




LOCAL_SERVING = {
    "bulbs" : {
        "processing" : bulb_buttons,
        "callback" : bulb_handler,
    },
    "servers" : 
        {
        "processing" : server_buttons,
        "callback" : server_handler,
    }

}


def get_local_buttons(category) -> tuple:
    return LOCAL_SERVING[category].keys()

def processing_local(category, ip) -> None:
    LOCAL_SERVING[category]["processing"](ip)




if __name__ == "__main__":
    get_local_data()
    