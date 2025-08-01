import os, random, asyncio, time, re, pytz
from Script import script
from database.users_db import db
from pyrogram import Client, filters, enums
from pyrogram.errors import *
from pyrogram.types import *
from info import BOT_USERNAME, URL, BATCH_PROTECT_CONTENT, ADMINS, PROTECT_CONTENT, OWNER_USERNAME, SUPPORT, PICS, FILE_PIC, CHANNEL, VERIFIED_LOG, LOG_CHANNEL, FSUB, BIN_CHANNEL, VERIFY_EXPIRE, BATCH_FILE_CAPTION, FILE_CAPTION, VERIFY_IMG, QR_CODE
from datetime import datetime
from web.utils.file_properties import get_hash
from utils import get_readable_time, verify_user, check_token, get_size
from web.utils import StartTime, __version__
from plugins.avbot import is_user_joined, av_verification, av_x_verification
import os
import json
import asyncio
import logging

logger = logging.getLogger(__name__)
BATCH_FILES = {}  

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    await message.react(emoji="🔥", big=True)
    user_id = message.from_user.id
    mention = message.from_user.mention
    me2 = (await client.get_me()).mention
    if FSUB:
        if not await is_user_joined(client, message):
            return
    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT.format(me2, user_id, mention))
    if len(message.command) == 1 or message.command[1] == "start":
        buttons = [[
            InlineKeyboardButton('➕ 𝗔𝗗𝗗 𝗠𝗘 𝗧𝗢 𝗬𝗢𝗨𝗥 𝗖𝗛𝗔𝗡𝗡𝗘𝗟 ➕', url='http://t.me/File_To_Link_Prime_Bot?startchannel=true')
        ],[
            InlineKeyboardButton('〄 ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ 〄', url=CHANNEL),
            InlineKeyboardButton('✪ ꜱᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ ✪', url=SUPPORT)
        ], [
            InlineKeyboardButton('〆 ʜᴇʟᴘ 〆', callback_data='help'),
            InlineKeyboardButton('〆 ᴀʙᴏᴜᴛ 〆', callback_data='about')
        ],[
            InlineKeyboardButton('✧ ᴄʀᴇᴀᴛᴏʀ ✧', url="https://t.me/Prime_Nayem")
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)

        m = await message.reply_sticker("CAACAgUAAxkBAAEBHsJnlRzxX8727obKStoAAczGV5EIGiwAAn0ZAAJKepFUmtCTESphePUeBA")
        await asyncio.sleep(3)
        await m.delete()

        await message.reply_photo(
            photo=PICS,
            caption=script.START_TXT.format(message.from_user.mention, BOT_USERNAME),
            reply_markup=reply_markup
        )
        return

    # ✅ Handle /start file_<id>
    msg = message.command[1]

    if msg.startswith("file_"):
        _, file_id = msg.split("_", 1)

        # Get the original message from BIN_CHANNEL
        original_message = await client.get_messages(int(BIN_CHANNEL), int(file_id))

        # Detect media
        media = original_message.document or original_message.video or original_message.audio
        caption = None

        if media:
            file_name = media.file_name or "Unnamed File"
            file_size = get_size(media.file_size)
            caption = FILE_CAPTION.format(CHANNEL, file_name)

        # Send with caption and protect_content
        return await client.copy_message(
            chat_id=message.from_user.id,
            from_chat_id=int(BIN_CHANNEL),
            message_id=int(file_id),
            caption=caption,
            protect_content=PROTECT_CONTENT
	)

    if msg.startswith("verify-"):
        try:
            _, userid, token = msg.split("-", 2)
        except ValueError:
            return await message.reply_text("<b>ʟɪɴᴋ ᴇxᴘɪʀᴇᴅ ᴛʀʏ ᴀɢᴀɪɴ...!</b>")

        if str(message.from_user.id) != str(userid):
            return await message.reply_text("<b>ʟɪɴᴋ ᴇxᴘɪʀᴇᴅ ᴛʀʏ ᴀɢᴀɪɴ...!</b>")

        is_valid = await check_token(client, userid, token)
        if is_valid:
            await message.reply_photo(
                photo=(VERIFY_IMG),
                caption=script.VERIFIED_COMPLETE_TEXT.format(message.from_user.mention),
                parse_mode=enums.ParseMode.HTML
	    )
            await verify_user(client, userid, token)
            await client.send_message(
                VERIFIED_LOG,
                script.VERIFIED_LOG_TEXT.format(
                message.from_user.mention,
                message.from_user.id,
                datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d %B %Y')
                )
            )
        else:
            return await message.reply_text("<b>ʟɪɴᴋ ᴇxᴘɪʀᴇᴅ ᴛʀʏ ᴀɢᴀɪɴ...!</b>")

    if msg.startswith("BATCH-"):
        file_id = msg.split("-", 1)[1]
        user_id = message.from_user.id
        if not await db.has_premium_access(user_id):
            verified = await av_x_verification(client, message)
            if not verified:
                return  # If not verified, exit
        sts = await message.reply("<b>Please wait...</b>")
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            try:
                downloaded_file = await client.download_media(file_id)
                with open(downloaded_file, "r", encoding="utf-8") as f:
                    msgs = json.load(f)
                os.remove(downloaded_file)
                BATCH_FILES[file_id] = msgs
            except Exception as e:
                await sts.edit("❌ FAILED to load file.")
                logger.exception("Unable to open batch JSON file.")
                return await client.send_message(LOG_CHANNEL, f"❌ UNABLE TO OPEN FILE: {e}")
        for msg in msgs:
            title = msg.get("title")
            size = get_size(int(msg.get("size", 0)))
            f_caption = msg.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption = BATCH_FILE_CAPTION.format(CHANNEL,
                        file_name=title or "",
                        file_size=size or "",
                        file_caption=f_caption or ""
                    )
                except Exception as e:
                    logger.warning(f"Caption formatting error: {e}")
                    f_caption = f_caption or title or ""

            if not f_caption:
                f_caption = title or "Untitled"
            try:
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=BATCH_PROTECT_CONTENT
                )
            except FloodWait as e:
                await asyncio.sleep(e.x)
                logger.warning(f"⏳ FloodWait: {e.x}s")
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=BATCH_PROTECT_CONTENT
                )
            except Exception as e:
                logger.error(f"❌ Failed to send media: {e}", exc_info=True)
                continue

            await asyncio.sleep(1)

        await sts.delete()
        return
	    
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "about":
        buttons = [[
	    InlineKeyboardButton('💻 sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ', callback_data="source_prime")
	],[
            InlineKeyboardButton('• ʜᴏᴍᴇ •', callback_data='start'),
	    InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        me2 = (await client.get_me()).mention
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(me2, me2, get_readable_time(time.time() - StartTime), __version__),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    
    elif query.data == "start":
        buttons = [[
	    InlineKeyboardButton('➕ 𝗔𝗗𝗗 𝗠𝗘 𝗧𝗢 𝗬𝗢𝗨𝗥 𝗖𝗛𝗔𝗡𝗡𝗘𝗟 ➕', url='http://t.me/File_To_Link_Prime_Bot?startchannel=true')
        ],[
            InlineKeyboardButton('〄 ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ 〄', url=CHANNEL),
	    InlineKeyboardButton('✪ ꜱᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ ✪', url=SUPPORT)
        ],[
            InlineKeyboardButton('〆 ʜᴇʟᴘ 〆', callback_data='help'),
            InlineKeyboardButton('〆 ᴀʙᴏᴜᴛ 〆', callback_data='about')
        ],[
            InlineKeyboardButton('✧ ᴄʀᴇᴀᴛᴏʀ ✧', url="https://t.me/Prime_Nayem")
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, BOT_USERNAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
	    )
	    
    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('• ᴀᴅᴍɪɴ •', callback_data='admincmd')
	],[
	    InlineKeyboardButton('• ʜᴏᴍᴇ •', callback_data='start'),
	    InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HELP_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )  

    elif query.data == "admincmd":
        #if user isnt admin then return
        if not query.from_user.id in ADMINS:
            return await query.answer('This Feature Is Only For Admins !' , show_alert=True)
        buttons = [[
            InlineKeyboardButton('• ʜᴏᴍᴇ •', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ADMIN_CMD_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
       )

    elif query.data == "premium_info":
        buttons = [[
		InlineKeyboardButton('🍁 ᴄʟɪᴄᴋ ᴀʟʟ ᴘʟᴀɴꜱ & ᴘʀɪᴄᴇ 🍁', callback_data='check_plan')
        ],[
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ ', callback_data='start')
	]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.PREMIUM_TEXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
	)

    elif query.data == "check_plan":
        buttons = [
            [
                InlineKeyboardButton(
                    "☆📸 ꜱᴇɴᴅ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ 📸☆",
                    url=f"https://t.me/{OWNER_USERNAME}"),
            ],[
                InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data='premium_info'),
                InlineKeyboardButton("• ᴄʟᴏꜱᴇ •", callback_data="close_data"),
	    ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CHECK_PLAN_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
	)

    elif query.data == "seeplans":
        btn = [[
            InlineKeyboardButton('🍁 ᴄʟɪᴄᴋ ᴀʟʟ ᴘʟᴀɴꜱ & ᴘʀɪᴄᴇ 🍁', callback_data='check_plan')
        ],[
            InlineKeyboardButton('❌ ᴄʟᴏsᴇ ❌', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(btn)
        m=await query.message.reply_sticker("CAACAgQAAxkBAAEiLZ9l7VMuTY7QHn4edR6ouHUosQQ9gwACFxIAArzT-FOmYU0gLeJu7x4E") 
        await m.delete()
        await query.message.reply_photo(
            photo=(QR_CODE),
            caption=script.PREMIUM_TEXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
	)

    # ⏩ Pagination: Next/Back
    elif query.data.startswith("filespage_"):
        page = int(query.data.split("_")[1])
        user_id = query.from_user.id	    
        files = await db.files.find({"user_id": user_id}).to_list(length=100)
        per_page = 7
        total_pages = (len(files) + per_page - 1) // per_page
        if not files or page < 1 or page > total_pages:
            return await query.answer("⚠️ Nᴏ ᴍᴏʀᴇ ғɪʟᴇꜱ.", show_alert=True)
        start = (page - 1) * per_page
        end = start + per_page
        btns = []
        for f in files[start:end]:
            name = f["file_name"][:40]
            btns.append([InlineKeyboardButton(name, callback_data=f"sendfile_{f['file_id']}")])
        nav_btns = []
        if page > 1:
            nav_btns.append(InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data=f"filespage_{page - 1}"))
        if page < total_pages:
            nav_btns.append(InlineKeyboardButton("➡️ Nᴇxᴛ", callback_data=f"filespage_{page + 1}"))
        nav_btns.append(InlineKeyboardButton("❌ ᴄʟᴏsᴇ ❌", callback_data="close_data"))
        btns.append(nav_btns)
        await query.message.edit_text(
            f"📁 Tᴏᴛᴀʟ ғɪʟᴇꜱ: {len(files)} | Pᴀɢᴇ {page}/{total_pages}",
            reply_markup=InlineKeyboardMarkup(btns)
        )
        return await query.answer()

    elif query.data.startswith("delfilespage_"):
        page = int(query.data.split("_")[1])
        user_id = query.from_user.id	    
        files = await db.files.find({"user_id": user_id}).to_list(length=100)
        per_page = 7
        total_pages = (len(files) + per_page - 1) // per_page
        if not files or page < 1 or page > total_pages:
            return await query.answer("⚠️ Nᴏ ᴍᴏʀᴇ ғɪʟᴇꜱ.", show_alert=True)
        start = (page - 1) * per_page
        end = start + per_page
        btns = []
        for f in files[start:end]:
            name = f["file_name"][:40]
            btns.append([InlineKeyboardButton(name, callback_data=f"deletefile_{f['file_id']}")])
        nav_btns = []
        if page > 1:
            nav_btns.append(InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data=f"delfilespage_{page - 1}"))
        if page < total_pages:
            nav_btns.append(InlineKeyboardButton("➡️ Nᴇxᴛ", callback_data=f"delfilespage_{page + 1}"))
        nav_btns.append(InlineKeyboardButton("❌ ᴄʟᴏsᴇ ❌", callback_data="close_data"))
        btns.append(nav_btns)
        await query.message.edit_text(
            f"📁 Tᴏᴛᴀʟ ғɪʟᴇꜱ: {len(files)} | Pᴀɢᴇ {page}/{total_pages}",
            reply_markup=InlineKeyboardMarkup(btns)
        )
        return await query.answer()

    elif query.data.startswith("sendfile_"):
        file_id = int(query.data.split("_")[1])
        user_id = query.from_user.id
        file_data = await db.files.find_one({"file_id": file_id, "user_id": user_id})
        if not file_data:
            return await query.answer("⚠️ Nᴏ ᴍᴏʀᴇ ғɪʟᴇꜱ.", show_alert=True)
        try:
            original_message = await client.get_messages(BIN_CHANNEL, file_id)
            media = original_message.document or original_message.video or original_message.audio
            caption = None
            if media:
                file_name = media.file_name or "Unnamed"
                file_size = get_size(media.file_size)
                caption = FILE_CAPTION.format(CHANNEL, file_name)
            await client.copy_message(
                chat_id=user_id,
                from_chat_id=BIN_CHANNEL,
                message_id=file_id,
                caption=caption,
                protect_content=PROTECT_CONTENT
            )
            return await query.answer()
        except Exception:
            return await query.answer("⚠️ Failed to send file.", show_alert=True)
		
    elif query.data.startswith("deletefile_"):
        file_msg_id = int(query.data.split("_")[1])
        user_id = query.from_user.id
        file_data = await db.files.find_one({"file_id": file_msg_id})
        if not file_data:
            return await query.answer("❌ Fɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ ᴏʀ ᴀʟʀᴇᴀᴅʏ ᴅᴇʟᴇᴛᴇᴅ.", show_alert=True)
        if file_data["user_id"] != user_id:
            return await query.answer("⚠️ Yᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴛᴏ ᴅᴇʟᴇᴛᴇ ᴛʜɪꜱ ғɪʟᴇ!", show_alert=True)
        await db.files.delete_one({"file_id": file_msg_id})
        try:
            await client.delete_messages(BIN_CHANNEL, file_msg_id)
        except:
            pass
        await query.answer("✅ Fɪʟᴇ ᴅᴇʟᴇᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ!", show_alert=True)
        await query.message.edit_text("🗑️ Fɪʟᴇ ʜᴀꜱ ʙᴇᴇɴ ᴅᴇʟᴇᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ.")

@Client.on_callback_query(filters.regex("source_prime"))
async def source_info_callback(client, callback_query):
    await callback_query.message.reply_photo(
        photo="https://i.postimg.cc/hvFZ93Ct/file-000000004188623081269b2440872960.png",
        caption=(
            "**ɴᴏᴛᴇ :**\n\n"
            "⚠️ ᴛʜɪꜱ ʙᴏᴛ ɪꜱ ᴀɴ ᴘʀɪᴠᴀᴛᴇ ꜱᴏᴜʀᴄᴇ ᴘʀᴏᴊᴇᴄᴛ\n\n"
            "ᴛʜɪs ʙᴏᴛ ʜᴀs ʟᴀsᴛᴇsᴛ ᴀɴᴅ ᴀᴅᴠᴀɴᴄᴇᴅ ꜰᴇᴀᴛᴜʀᴇs⚡️\n\n"
            "▸ ᴅᴏɴ'ᴛ ᴡᴏʀʀʏ\n"
            "▸ ɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ʟɪᴋᴇ ᴛʜɪꜱ ʙᴏᴛ ᴄᴏɴᴛᴀᴄᴛ ᴍᴇ..!\n"
            "▸ ɪ ᴡɪʟʟ ᴄʀᴇᴀᴛᴇ ᴀ ʙᴏᴛ ꜰᴏʀ ʏᴏᴜ\n\n"
            "⇒ ᴄᴏɴᴛᴀᴄᴛ ᴍᴇ - <a href='https://t.me/Prime_Admin_Support_ProBot'>♚ ᴀᴅᴍɪɴ ♚</a>"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("♚ ᴀᴅᴍɪɴ ♚", url="https://t.me/Prime_Admin_Support_ProBot")],
            [InlineKeyboardButton("• ᴄʟᴏsᴇ •", callback_data="close_data")]
        ]),
        parse_mode=enums.ParseMode.HTML
    )
    return await callback_query.answer()


@Client.on_message(filters.private & filters.command("files"))
async def list_user_files(client, message: Message):
    user_id = message.from_user.id
    files = await db.files.find({"user_id": user_id}).to_list(length=100)
    if not files:
        return await message.reply_text("❌ Yᴏᴜ ʜᴀᴠᴇɴ'ᴛ ᴜᴘʟᴏᴀᴅᴇᴅ ᴀɴʏ ғɪʟᴇꜱ.")
    page = 1
    per_page = 7
    start = (page - 1) * per_page
    end = start + per_page
    total_pages = (len(files) + per_page - 1) // per_page
    btns = []
    for f in files[start:end]:
        name = f["file_name"][:40]
        btns.append([InlineKeyboardButton(name, callback_data=f"sendfile_{f['file_id']}")])
    nav_btns = []
    if page < total_pages:
        nav_btns.append(InlineKeyboardButton("➡️ Nᴇxᴛ", callback_data=f"filespage_{page + 1}"))
    nav_btns.append(InlineKeyboardButton("❌ ᴄʟᴏsᴇ ❌", callback_data="close_data"))
    btns.append(nav_btns)
    await message.reply_photo(photo=FILE_PIC,
        caption=f"📁 Tᴏᴛᴀʟ ғɪʟᴇꜱ: {len(files)} | Pᴀɢᴇ {page}/{total_pages}",
        reply_markup=InlineKeyboardMarkup(btns)
    )

@Client.on_message(filters.private & filters.command("del_files"))
async def delete_files_list(client, message):
    user_id = message.from_user.id
    files = await db.files.find({"user_id": user_id}).to_list(length=100)
    if not files:
        return await message.reply_text("❌ Yᴏᴜ ʜᴀᴠᴇɴ'ᴛ ᴜᴘʟᴏᴀᴅᴇᴅ ᴀɴʏ ғɪʟᴇꜱ.")
    page = 1
    per_page = 7
    start = (page - 1) * per_page
    end = start + per_page
    total_pages = (len(files) + per_page - 1) // per_page
    btns = []
    for f in files[start:end]:
        name = f["file_name"][:40]
        btns.append([InlineKeyboardButton(name, callback_data=f"deletefile_{f['file_id']}")])
    nav_btns = []
    if page < total_pages:
        nav_btns.append(InlineKeyboardButton("➡️ Nᴇxᴛ", callback_data=f"delfilespage_{page + 1}"))
    nav_btns.append(InlineKeyboardButton("❌ ᴄʟᴏsᴇ ❌", callback_data="close_data"))
    btns.append(nav_btns)
    await message.reply_photo(photo=FILE_PIC,
        caption=f"📁 Tᴏᴛᴀʟ ғɪʟᴇꜱ: {len(files)} | Pᴀɢᴇ {page}/{total_pages}",
        reply_markup=InlineKeyboardMarkup(btns)
    )

@Client.on_message(filters.command("about"))
async def about(client, message):
    buttons = [[
       InlineKeyboardButton('💻 sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ', callback_data="source_prime")
    ],[
       InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    me2 = (await client.get_me()).mention
    await message.reply_text(
        text=script.ABOUT_TXT.format(me2, me2, get_readable_time(time.time() - StartTime), __version__),
        disable_web_page_preview=True, 
        reply_markup=reply_markup
    )

 
@Client.on_message(filters.command("help"))
async def help(client, message):
    btn = [[
       InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
    ]]
    reply_markup = InlineKeyboardMarkup(btn)
    await message.reply_text(
        text=script.HELP2_TXT,
        disable_web_page_preview=True, 
        reply_markup=reply_markup
)
