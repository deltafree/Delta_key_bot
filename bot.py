import asyncio
import logging
import time
import random
import string
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8969469331:AAEJ9sbRMsOsyPNKXDbw1G2HJ2projaP7PU"
ADMIN_ID = 761064374
YOUTUBE_URL = "https://youtube.com/@deltascrip-z2k"
TG_CHANNEL = "@your_channel"
DATA_FILE = "data.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def loadData():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "keys": {}, "control": {"global_enabled": True, "blocked": {}}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "users" not in data:
            data["users"] = {}
        if "keys" not in data:
            data["keys"] = {}
        if "control" not in data:
            data["control"] = {"global_enabled": True, "blocked": {}}
        if "blocked" not in data["control"]:
            data["control"]["blocked"] = {}
        return data
    except Exception as e:
        print("loadData error:", e)
        return {"users": {}, "keys": {}, "control": {"global_enabled": True, "blocked": {}}}


def saveData(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("saveData error:", e)


def formatTimeLeft(seconds):
    if seconds <= 0:
        return "expired"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return str(h) + "h " + str(m) + "min"
    return str(m) + "min"


def generateKey(permanent=False):
    if permanent:
        return "GUM-PERM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return "GUM-" + "-".join(
        "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        for i in range(2)
    )


@dp.message(Command("start"))
async def cmdStart(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Users", callback_data="adminUsers")],
            [InlineKeyboardButton(text="Stats", callback_data="adminStats")],
            [InlineKeyboardButton(text="Keys", callback_data="adminKeys")],
            [
                InlineKeyboardButton(text="OFF ALL", callback_data="adminOff"),
                InlineKeyboardButton(text="ON ALL", callback_data="adminOn"),
            ],
        ])
        await msg.answer("Gum Hub Admin\n\nChoose action:", reply_markup=kb)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Get Key", callback_data="userGetkey")],
        [InlineKeyboardButton(text="YouTube", url=YOUTUBE_URL)],
    ])
    await msg.answer(
        "Welcome to Gum Hub!\n\nPress Get Key to receive your key (24 hours).",
        reply_markup=kb
    )


@dp.callback_query(lambda c: c.data == "userGetkey")
async def onGetKey(call: types.CallbackQuery):
    userId = str(call.from_user.id)
    username = call.from_user.username or call.from_user.first_name or "user"

    data = loadData()

    if userId not in data["users"]:
        data["users"][userId] = {
            "name": username,
            "username": call.from_user.username or "",
            "blocked": False,
            "last_key": None,
            "keys_used": 0,
            "first_seen": int(time.time()),
        }

    user = data["users"][userId]

    if user.get("blocked"):
        saveData(data)
        await call.answer("You are blocked", show_alert=True)
        return

    now = int(time.time())
    if user.get("last_key_time") and (now - user["last_key_time"]) < 24 * 3600:
        left = 24 * 3600 - (now - user["last_key_time"])
        await call.answer("Wait " + formatTimeLeft(left) + " for next key", show_alert=True)
        return

    key = generateKey(False)
    expires = now + 24 * 3600

    user["last_key"] = key
    user["last_key_time"] = now
    user["keys_used"] = user.get("keys_used", 0) + 1
    user["name"] = username

    data["keys"][key] = {
        "user_id": userId,
        "user": username,
        "expires": expires,
        "permanent": False,
        "active": True,
        "created": now,
    }

    saveData(data)

    expStr = time.strftime("%d.%m %H:%M", time.localtime(expires))
    await call.message.answer(
        "Your key:\n\n" + key + "\n\nValid 24h until " + expStr
    )
    await call.answer("Key sent")


@dp.message(Command("newperm"))
async def cmdNewperm(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    key = generateKey(True)
    now = int(time.time())
    data = loadData()
    data["keys"][key] = {
        "user_id": None, "user": None, "expires": None,
        "permanent": True, "active": True, "created": now,
    }
    saveData(data)
    await msg.answer("Permanent key:\n\n" + key)


@dp.message(Command("newkey24"))
async def cmdNewkey24(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    key = generateKey(False)
    now = int(time.time())
    data = loadData()
    data["keys"][key] = {
        "user_id": None, "user": None, "expires": now + 24 * 3600,
        "permanent": False, "active": True, "created": now,
    }
    saveData(data)
    await msg.answer("Key 24h:\n\n" + key)


@dp.message(Command("status"))
async def cmdStatus(msg: types.Message):
    parts = msg.text.split(maxsplit=1)

    if msg.from_user.id == ADMIN_ID and len(parts) > 1:
        target = parts[1].strip().lower()
        data = loadData()
        for uid, user in data["users"].items():
            if user.get("name", "").lower() == target:
                if user.get("last_key"):
                    keyData = data["keys"].get(user["last_key"])
                    if keyData:
                        if keyData.get("permanent"):
                            await msg.answer("User " + target + "\nKey: " + user["last_key"] + "\nStatus: PERMANENT")
                            return
                        left = keyData["expires"] - int(time.time())
                        await msg.answer("User " + target + "\nKey: " + user["last_key"] + "\nLeft: " + formatTimeLeft(left))
                        return
        await msg.answer("User " + target + ": no key")
        return

    userId = str(msg.from_user.id)
    data = loadData()
    user = data["users"].get(userId)
    if not user or not user.get("last_key"):
        await msg.answer("You have no key. Press Get Key.")
        return
    keyData = data["keys"].get(user["last_key"])
    if not keyData:
        await msg.answer("Key not found")
        return
    if keyData.get("permanent"):
        await msg.answer("Your key:\n\n" + user["last_key"] + "\n\nPermanent")
        return
    left = keyData["expires"] - int(time.time())
    await msg.answer("Your key:\n\n" + user["last_key"] + "\n\nLeft: " + formatTimeLeft(left))


@dp.callback_query(lambda c: c.data.startswith("admin"))
async def onAdminButton(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("No access", show_alert=True)
        return

    action = call.data.replace("admin", "")

    if action == "Users":
        data = loadData()
        users = data.get("users", {})
        if not users:
            await call.message.answer("No users yet")
            await call.answer()
            return
        for userId, info in users.items():
            name = info.get("name", "unknown")
            blocked = info.get("blocked", False)
            keysUsed = info.get("keys_used", 0)
            status = "BLOCKED" if blocked else "Active"
            text = "User: " + name + "\nID: " + userId + "\nStatus: " + status + "\nKeys used: " + str(keysUsed)
            if blocked:
                btn = InlineKeyboardButton(text="Unblock", callback_data="unblock:" + userId)
            else:
                btn = InlineKeyboardButton(text="Block", callback_data="block:" + userId)
            kb = InlineKeyboardMarkup(inline_keyboard=[[btn]])
            await call.message.answer(text, reply_markup=kb)
        await call.answer()

    elif action == "Stats":
        data = loadData()
        users = data.get("users", {})
        total = len(users)
        blocked = sum(1 for u in users.values() if u.get("blocked"))
        totalKeys = sum(u.get("keys_used", 0) for u in users.values())
        await call.message.answer(
            "Stats\n\nTotal: " + str(total) +
            "\nActive: " + str(total - blocked) +
            "\nBlocked: " + str(blocked) +
            "\nKeys issued: " + str(totalKeys)
        )
        await call.answer()

    elif action == "Keys":
        data = loadData()
        keys = data.get("keys", {})
        if not keys:
            await call.message.answer("No keys")
            await call.answer()
            return
        now = int(time.time())
        lines = ["Keys: " + str(len(keys))]
        for k, info in keys.items():
            user = info.get("user") or "none"
            if info.get("permanent"):
                lines.append("PERM " + k + " -> " + user)
            elif info.get("expires"):
                left = info["expires"] - now
                if left > 0:
                    lines.append("ACTIVE " + k + " -> " + user + " (" + formatTimeLeft(left) + ")")
                else:
                    lines.append("EXPIRED " + k + " -> " + user)
        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:4000] + "\n..."
        await call.message.answer(text)
        await call.answer()

    elif action == "Off":
        data = loadData()
        data["control"]["global_enabled"] = False
        saveData(data)
        await call.answer("ALL OFF", show_alert=True)

    elif action == "On":
        data = loadData()
        data["control"]["global_enabled"] = True
        saveData(data)
        await call.answer("ALL ON", show_alert=True)


@dp.callback_query(lambda c: c.data.startswith("block") or c.data.startswith("unblock"))
async def onBlockButton(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("No access", show_alert=True)
        return

    if call.data.startswith("block"):
        userId = call.data.split(":")[1]
        data = loadData()
        if userId in data["users"]:
            data["users"][userId]["blocked"] = True
            saveData(data)
            name = data["users"][userId].get("name", "user")
            await call.answer(name + " blocked")
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Unblock", callback_data="unblock:" + userId)
            ]])
            await call.message.edit_reply_markup(reply_markup=kb)

    elif call.data.startswith("unblock"):
        userId = call.data.split(":")[1]
        data = loadData()
        if userId in data["users"]:
            data["users"][userId]["blocked"] = False
            saveData(data)
            name = data["users"][userId].get("name", "user")
            await call.answer(name + " unblocked")
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Block", callback_data="block:" + userId)
            ]])
            await call.message.edit_reply_markup(reply_markup=kb)


async def main():
    logging.basicConfig(level=logging.INFO)
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
