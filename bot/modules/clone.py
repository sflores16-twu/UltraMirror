import random
import string

from telegram.ext import CommandHandler

from bot.helper.mirror_utils.upload_utils import gdriveTools
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, deleteMessage, delete_all_messages, update_all_messages, sendStatusMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot import dispatcher, LOGGER, CLONE_LIMIT, STOP_DUPLICATE, download_dict, download_dict_lock, Interval
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_gdrive_link, is_gdtot_link, new_thread
from bot.helper.mirror_utils.download_utils.direct_link_generator import gdtot
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException

@new_thread
def cloneNode(update, context):
    args = update.message.text.split(" ", maxsplit=1)
    reply_to = update.message.reply_to_message
    if len(args) > 1:
        link = args[1]
    elif reply_to is not None:
        link = reply_to.text
    else:
        link = ''
    gdtot_link = is_gdtot_link(link)
    if gdtot_link:
        try:
            msg = sendMessage(f"Processing: <code>{link}</code>", context.bot, update)
            link = gdtot(link)
            deleteMessage(context.bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(context.bot, msg)
            return sendMessage(str(e), context.bot, update)
    if is_gdrive_link(link):
        gd = gdriveTools.GoogleDriveHelper()
        res, size, name, files = gd.helper(link)
        if res != "":
            return sendMessage(res, context.bot, update)
        if STOP_DUPLICATE:
            LOGGER.info('Checking File/Folder if already in Drive...')
            smsg, button = gd.drive_list(name, True, True)
            if smsg:
                msg3 = "File/Folder is already available in Drive.\nHere are the search results:"
                sendMarkup(msg3, context.bot, update, button)
                if gdtot_link:
                    gd.deletefile(link)
                return
        if CLONE_LIMIT is not None:
            LOGGER.info('Checking File/Folder Size...')
            if size > CLONE_LIMIT * 1024**3:
                msg2 = f'Failed, Clone limit is {CLONE_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(size)}.'
                return sendMessage(msg2, context.bot, update)
        if files <= 10:
            msg = sendMessage(f"Cloning: <code>{link}</code>", context.bot, update)
            result, button = gd.clone(link)
            deleteMessage(context.bot, msg)
        else:
            drive = gdriveTools.GoogleDriveHelper(name)
            gid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=12))
            clone_status = CloneStatus(drive, size, update, gid)
            with download_dict_lock:
                download_dict[update.message.message_id] = clone_status
            sendStatusMessage(update, context.bot)
            result, button = drive.clone(link)
            with download_dict_lock:
                del download_dict[update.message.message_id]
                count = len(download_dict)
            try:
                if count == 0:
                    Interval[0].cancel()
                    del Interval[0]
                    delete_all_messages()
                else:
                    update_all_messages()
            except IndexError:
                pass
        if update.message.from_user.username:
            uname = f'@{update.message.from_user.username}'
        else:
            uname = f'<a href="tg://user?id={update.message.from_user.id}">{update.message.from_user.first_name}</a>'
        if uname is not None:
            cc = f'\n\n𝘾𝙡𝙤𝙣𝙚𝙙 𝙗𝙮: {uname}'
            men = f'{uname} '
            msg_g = f'\n\n - 𝙽𝚎𝚟𝚎𝚛 𝚂𝚑𝚊𝚛𝚎 𝙶-𝙳𝚛𝚒𝚟𝚎\n - 𝙽𝚎𝚟𝚎𝚛 𝚂𝚑𝚊𝚛𝚎 𝙸𝚗𝚍𝚎𝚡 𝙻𝚒𝚗𝚔\n - 𝙹𝚘𝚒𝚗 𝚃𝙳 𝚃𝚘 𝙰𝚌𝚌𝚎𝚜𝚜 𝙶-𝙳𝚛𝚒𝚟𝚎 𝙻𝚒𝚗𝚔'
            fwdpm = f'\n\n𝐘𝐨𝐮 𝐂𝐚𝐧 𝐅𝐢𝐧𝐝 𝐔𝐩𝐥𝐨𝐚𝐝 𝐈𝐧 𝐏𝐫𝐢𝐯𝐚𝐭𝐞 𝐂𝐡𝐚𝐭 𝐨𝐫 𝐂𝐥𝐢𝐜𝐤 𝐛𝐮𝐭𝐭𝐨𝐧 𝐛𝐞𝐥𝐨𝐰 𝐭𝐨 𝐒𝐞𝐞 𝐚𝐭 𝐥𝐨𝐠 𝐜𝐡𝐚𝐧𝐧𝐞𝐥'
            men = f'{uname} '
        if button in ["cancelled", ""]:
            sendMessage(men + result, context.bot, update)
        else:
            logmsg = sendLog(result + cc + msg_g, context.bot, update, button)
            if logmsg:
                log_m = f"\n\n<b>Link Uploaded, Click Below Button</b>"
                sendMarkup(result + cc + fwdpm, context.bot, update, InlineKeyboardMarkup([[InlineKeyboardButton(text="𝐂𝐋𝐈𝐂𝐊 𝐇𝐄𝐑𝐄", url=logmsg.link)]]))
                sendPrivate(result + cc + msg_g, context.bot, update, button)
        if gdtot_link:
            gd.deletefile(link)
    else:
        sendMessage('Send Gdrive or gdtot link along with command or by replying to the link by command', context.bot, update)

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(clone_handler)
