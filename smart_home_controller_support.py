import os
import shutil
from telegram import Update, InlineKeyboardButton, KeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from time import sleep
import asyncio

#bulbs
from yeelight import Bulb, BulbException
#PCs
from wakeonlan import send_magic_packet

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def data_dir() -> str:
    """State directory: DATA_DIR env, else ./data next to the app."""
    d = os.environ.get("DATA_DIR", "").strip()
    if d:
        return d
    return os.path.join(ROOT_DIR, "data")


def secure_data_path() -> str:
    return os.path.join(data_dir(), "secure_data.txt")


def session_data_path() -> str:
    return os.path.join(data_dir(), "session_data.txt")


def _token_from_env() -> str | None:
    for key in ("TELEGRAM_BOT_TOKEN", "API_KEY_CTR"):
        v = os.environ.get(key, "").strip()
        if v:
            return v
    return None


def _admins_from_env() -> dict | None:
    raw = os.environ.get("BOT_ADMINS_JSON", "").strip()
    if not raw:
        return None
    import json

    data = json.loads(raw)
    out: dict = {}
    for username, val in data.items():
        if isinstance(val, dict):
            out[username] = {"id": str(val.get("id", "0"))}
        else:
            out[username] = {"id": str(val)}
    return out


def _admins_from_secure_file_lines(lines: list[str]) -> dict:
    return {
        line.split()[0]: {"id": line[:-1].split()[1]}
        for line in lines
        if line.strip()
    }


def update_admins_list_file(ADMINS):
    id = "id"
    _, API_TOKEN, _ = get_secure_data()
    path = secure_data_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="ASCII") as f:
        f.write(f"API_KEY_CTR {API_TOKEN}\n")
        f.write("ADMINS\n")
        for admin in ADMINS:
            f.write(f"{admin} {ADMINS[admin][id]}\n")


def update_verified_list_file(VERIFIED):
    id = "id"
    path = session_data_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="ASCII") as f:
        for user in VERIFIED:
            f.write(f"{user} {VERIFIED[user][id]}")


def get_secure_data() -> list[dict]:
    """Telegram token: non-empty key from secure_data.txt wins, else env. Admins: file or BOT_ADMINS_JSON."""
    admins_env = _admins_from_env()
    s_path = secure_data_path()
    file_admins: dict | None = None
    token: str | None = None

    if os.path.exists(s_path):
        with open(s_path, "r", encoding="ASCII") as f:
            first = f.readline()
            from_file = first.split(" ", 1)[1].strip() if " " in first else first.strip()
            f.readline()
            lines = f.readlines()
        file_admins = _admins_from_secure_file_lines(lines)
        token = from_file if from_file else _token_from_env()
    else:
        token = _token_from_env()
        if token is None:
            raise FileNotFoundError(
                f"No token: set TELEGRAM_BOT_TOKEN or create {s_path} "
                f"(first line: API_KEY_CTR <token>)."
            )

    # Prefer non-empty secure_data file so admin chat ids updated at runtime persist
    # even when BOT_ADMINS_JSON is set for first boot.
    if file_admins:
        ADMINS = file_admins
    elif admins_env is not None:
        ADMINS = admins_env
    elif file_admins is not None:
        ADMINS = file_admins
    else:
        raise ValueError(
            "No admins: set BOT_ADMINS_JSON or provide ADMINS lines in secure_data.txt "
            f"({s_path})."
        )

    if not token:
        raise ValueError("Telegram token missing (TELEGRAM_BOT_TOKEN or file).")

    API_TOKEN = token
    print(ADMINS, API_TOKEN)

    sess = session_data_path()
    if os.path.exists(sess):
        with open(sess, "r") as f:
            VALDATED_USERS = {
                line.split()[0]: {"id": line[:-1].split()[1]}
                for line in f.readlines()
                if line.strip()
            }
    else:
        VALDATED_USERS = {}

    return [ADMINS, API_TOKEN, VALDATED_USERS]

def get_local_data() -> dict[dict]:
    local_path = os.path.join(data_dir(), "local_data.txt")
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="UTF8") as f:
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


def reload_data() -> tuple[dict, dict, str, dict]:
    """Re-read all files in DATA_DIR and refresh module-level caches.

    Returns the fresh (LOCALS, ADMINS, API_TOKEN, VALDATED_USERS).
    Note: API_TOKEN is updated in-memory, but the running Telegram client is
    bound to the token it started with — token changes still need a restart.
    """
    global LOCALS, ADMINS, API_TOKEN, VALDATED_USERS
    new_locals = get_local_data() or {}
    new_admins, new_token, new_validated = get_secure_data()
    LOCALS = new_locals
    ADMINS = new_admins
    API_TOKEN = new_token
    VALDATED_USERS = new_validated
    return new_locals, new_admins, new_token, new_validated

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

#_______________PC sections _______________#
from wakeonlan import send_magic_packet
async def WakeUpNeo(pc_mac_adr):
    print(pc_mac_adr)
    send_magic_packet(str(pc_mac_adr))
    return 0


@Authorized_Only
async def pc_buttons(update, context):
    # список кнопок
    print("PC section")
    keyboard = [
        [ 
            InlineKeyboardButton(name+' ' + emoji, callback_data=name) for name,emoji in zip(LOCALS["pcs"].keys(), ['\U0001f420','\u26B0\uFE0F'])

        ],
        [InlineKeyboardButton("Отмена", callback_data="None")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Какой секс включаем?', reply_markup=reply_markup)
    return "pcs"
    
@Can_be_cancelled
async def pc_handler(update, context):
    query = update.callback_query
    variant = query.data
    pc_wakeup_task = asyncio.create_task(WakeUpNeo(LOCALS["pcs"][variant]))
    await pc_wakeup_task
    await query.edit_message_text(text=f"Сигнал отправлен")
    return ConversationHandler.END

#_______________Ping sections _______________#

PING_REFRESH_CB = "__ping_refresh__"


async def _ping_host(host: str, timeout: float = 1.5) -> bool:
    """Single ICMP probe via system `ping`. Returns True if reachable."""
    if shutil.which("ping") is None:
        return False
    wait_s = max(1, int(round(timeout)))
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", str(wait_s), host,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except (FileNotFoundError, OSError):
        return False
    try:
        rc = await asyncio.wait_for(proc.wait(), timeout=wait_s + 1.0)
        return rc == 0
    except asyncio.TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass
        return False


async def get_ping_states() -> list[str]:
    """Run ICMP probes for every host in LOCALS['ping'] in parallel."""
    if not LOCALS or "ping" not in LOCALS:
        return []
    hosts = list(LOCALS["ping"].values())
    results = await asyncio.gather(*[_ping_host(h) for h in hosts])
    return ["\u2705" if ok else "\u274C" for ok in results]


def _ping_keyboard(states: list[str]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"{name} ({host}) {state}", callback_data=name)]
        for (name, host), state in zip(LOCALS["ping"].items(), states)
    ]
    rows.append([InlineKeyboardButton("\U0001F504 Обновить", callback_data=PING_REFRESH_CB)])
    rows.append([InlineKeyboardButton("Отмена", callback_data="None")])
    return InlineKeyboardMarkup(rows)


@Authorized_Only
async def ping_buttons(update, context):
    if not LOCALS or "ping" not in LOCALS or not LOCALS["ping"]:
        await update.message.reply_text(
            "Раздел !ping не задан в local_data.txt"
        )
        return ConversationHandler.END
    states = await get_ping_states()
    await update.message.reply_text(
        "Доступность устройств:",
        reply_markup=_ping_keyboard(states),
    )
    return "ping"


@Can_be_cancelled
async def ping_handler(update, context):
    query = update.callback_query
    variant = query.data
    await query.answer()

    if variant == PING_REFRESH_CB:
        states = await get_ping_states()
        await query.edit_message_text(
            "Доступность устройств:",
            reply_markup=_ping_keyboard(states),
        )
        return "ping"

    host = LOCALS.get("ping", {}).get(variant)
    if host is None:
        await query.edit_message_text(f"Неизвестное устройство: {variant}")
        return ConversationHandler.END
    ok = await _ping_host(host, timeout=2.0)
    status = "доступен \u2705" if ok else "недоступен \u274C"
    await query.edit_message_text(text=f"{variant} ({host}): {status}")
    return ConversationHandler.END


#_____________________end__________________#



LOCAL_SERVING = {
    "bulbs" : {
        "processing" : bulb_buttons,
        "callback" : bulb_handler,
    },
    # "servers" : 
    #     {
    #     "processing" : server_buttons,
    #     "callback" : server_handler,
    # },
    "pcs" : 
        {
        "processing" : pc_buttons,
        "callback" : pc_handler,
    },
    "ping": {
        "processing": ping_buttons,
        "callback": ping_handler,
    },

}


def get_local_buttons(category) -> tuple:
    return LOCAL_SERVING[category].keys()

def processing_local(category, ip) -> None:
    LOCAL_SERVING[category]["processing"](ip)




if __name__ == "__main__":
    get_local_data()
    