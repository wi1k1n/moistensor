import logging, hashlib, random, secrets, threading
import time, datetime as dt, pickle
from typing import Dict, List, Set
from collections.abc import Callable

import telegram.constants
from telegram import Update, User, Message
from telegram.ext import (
    Updater,
    Dispatcher,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    PicklePersistence,
    BasePersistence
)
from telegram.ext.utils.types import BD
from remoteDevice import RemotePacket, RemoteDevice
from deviceManager import DeviceManager

try:
    from config import *
except:
    pass
finally:
    DEBUG = DEBUG if 'DEBUG' in globals() else False

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


class TGUser:
    def __init__(self, uid: int, pmChatId: int, admin: bool = False):
        self.uid: int = uid
        self.admin: bool = admin
        self.pmChatId: int = pmChatId


class SubscribedChat:
    def __init__(self, chat_id: int):
        self.chat_id: int = chat_id
        self.deviceList: List[RemoteDevice] = []

    def appendDevice(self, device: RemoteDevice | int):
        self.deviceList.append(RemoteDevice(device) if type(device) == int else device)

    def removeDevice(self, device: RemoteDevice | int):
        self.deviceList.remove(device)


class TelegramBot:
    def __init__(self, _token: str, persistenseFileName: str, deviceManager: DeviceManager | None):
        self.TOKEN: str = _token
        self.deviceManager = deviceManager if deviceManager else DeviceManager()

        self.WAITING_FOR_PASSWORD,\
            self.IN_MAIN_STATE,\
            self.IGNORE = range(3)

        self.AUTH_INITIAL_ATTEMPTS = 4
        self.SEND_MESSAGE_ATTEMPTS = 3
        self.SEND_MESSAGE_REATTEMPT_DELAY = 0.5  # in seconds

        self.persistence: PicklePersistence = PicklePersistence(filename=persistenseFileName)
        self.updater: Updater = Updater(self.TOKEN, persistence=self.persistence)
        self.dispatcher: Dispatcher = self.updater.dispatcher

        self.dispatcher.add_handler(ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                self.WAITING_FOR_PASSWORD: [
                    CommandHandler('start', self.start),
                    MessageHandler(Filters.text, self.checkPassCode),
                ],
                self.IN_MAIN_STATE: [
                    CommandHandler('devices', self.showDevices),
                    CommandHandler('visualize', self.visualizeDevice, pass_args=True),
                    CommandHandler('monitor', self.monitorDevice, pass_args=True),
                    MessageHandler(Filters.text, self.mainMenuSink),
                ],
                self.IGNORE: []
            },
            fallbacks=[],
            name='Moistensor_v0.3',
            persistent=True
        ))


    @property
    def authorizedUsers(self):
        if not ('authorizedUsers' in self.dispatcher.bot_data):
            self.dispatcher.bot_data['authorizedUsers'] = dict()
        return self.dispatcher.bot_data['authorizedUsers']
    @property
    def subscribedChats(self):
        if not ('subscribedChats' in self.dispatcher.bot_data):
            self.dispatcher.bot_data['subscribedChats'] = dict()
        return self.dispatcher.bot_data['subscribedChats']


    def startBot(self, blockThread = False) -> None:
        """Run the bot."""
        self.updater.start_polling()
        if blockThread:
            self.updater.idle()
    def foreground(self):
        self.updater.idle()
    def stopBot(self):
        self.updater.stop()

    def generatePassCode(self, usr: User) -> str:
        dg = hashlib.sha224(secrets.token_bytes(8) + str(usr.id).encode('utf-8')).digest()
        return str(int.from_bytes(random.sample(dg, 4), 'big'))

    def start(self, upd: Update, ctx: CallbackContext) -> int | None:
        if not upd.message:
            return self.IN_MAIN_STATE

        if upd.effective_user.is_bot:
            return self.IGNORE
        if upd.effective_user.id in self.authorizedUsers:
            upd.message.reply_text('You are already authorized. Try /help command.')
            return self.IN_MAIN_STATE
        if upd.effective_chat.type != 'private':
            return  # TODO: handle group chats properly
        if DEBUG:
            upd.message.reply_text('!!!DEBUG MODE ON!!! No authentication required!')
            self.authorizedUsers[upd.effective_user.id] = TGUser(upd.effective_user.id, upd.effective_chat.id, True)
            self.subscribedChats[upd.message.chat_id] = SubscribedChat(upd.message.chat_id)
            return self.IN_MAIN_STATE

        upd.message.reply_text(
            "Welcome to Moistensor Bot. Please authorize yourself as administrator with a code from the console. "
            "Or ask administrator for the authorization code."
        )
        adminPassCode = self.generatePassCode(upd.effective_user)
        ctx.user_data['adminPassCode'] = adminPassCode
        ctx.user_data['authAttempts'] = self.AUTH_INITIAL_ATTEMPTS
        ctx.user_data['banned'] = False
        print('New user: [{0}] {1} | Passcode: {2}'.format(upd.effective_user.id, upd.effective_user.name, adminPassCode))

        # Check if there's already administrators
        adminIds = [tguser.pmChatId for (_, tguser) in self.authorizedUsers.items() if tguser.admin]
        if len(adminIds):
            userPassCode = self.generatePassCode(upd.effective_user)
            while userPassCode == adminPassCode:
                userPassCode = self.generatePassCode(upd.effective_user)
            ctx.user_data['userPassCode'] = userPassCode
            self.broadcastMessageToChats(adminIds, 'New user: [{0}] {1} | Passcode: {2}'.format(upd.effective_user.id, upd.effective_user.name, userPassCode))

        return self.WAITING_FOR_PASSWORD

    def checkPassCode(self, upd: Update, ctx: CallbackContext) -> int:
        if not upd.message:
            return self.IN_MAIN_STATE

        # Assumed to not being accessible to bots and not in private chats (as handled earlier)
        admin = False
        if 'adminPassCode' in ctx.user_data and upd.message.text == ctx.user_data['adminPassCode']:
            msg = 'Successfully authorized as Admin!'
            admin = True
        elif 'userPassCode' in ctx.user_data and upd.message.text == ctx.user_data['userPassCode']:
            msg = 'Successfully authorized!'
        else:
            ctx.user_data['authAttempts'] -= 1
            if ctx.user_data['authAttempts'] <= 0:
                ctx.user_data['banned'] = True
                upd.message.reply_text(
                    'No more authorization attempts. You are banned. Contact administrator for further information'
                )
                return self.IGNORE
            else:
                upd.message.reply_text(
                    'Wrong pass code. Try again (' + str(ctx.user_data['authAttempts']) + ' attempts left)'
                )
            return self.WAITING_FOR_PASSWORD

        upd.message.reply_text(msg)
        self.authorizedUsers[upd.effective_user.id] = TGUser(upd.effective_user.id, upd.effective_chat.id, admin)
        self.subscribedChats[upd.message.chat_id] = SubscribedChat(upd.message.chat_id)  # TODO: remove this as it needs to be handled smarter through user interaction

        return self.IN_MAIN_STATE

    def mainMenuSink(self, upd: Update, ctx: CallbackContext) -> int:
        if not upd.message:
            return self.IN_MAIN_STATE

        upd.message.reply_text(
            'Use /help to check valid commands'
        )
        return self.IN_MAIN_STATE

    def showDevices(self, upd: Update, ctx: CallbackContext) -> int:
        if not upd.message:
            return self.IN_MAIN_STATE

        repl = 'List of devices:\n'
        for (d, v) in self.deviceManager.devices.items():
            m = v.latestMeasurement
            c = v.latestCalibration
            l = v.entries
            if m and c:
                repl += '&gt; Device#{0}: <b>{2}</b> ({5}m ago) [{1} .. {3}] every {4}m ({6}m up)\n' \
                        '       {7} updates since {8}'\
                    .format(d.id, c.calibrationWet, m.measurement, c.calibrationDry, c.interval, round((dt.datetime.now() - m.timestamp).total_seconds() / 60),
                            m.deviceTimeStamp if m.timestamp > c.timestamp else c.deviceTimeStamp,
                            len(l), str(min(l, key=lambda x:x.timestamp).timestamp.strftime('%Y-%m-%d %H:%M:%S')))
            else:
                repl += 'Device#{0}: None'.format(d.id)
        upd.message.reply_text(
            repl.strip(), parse_mode=telegram.constants.PARSEMODE_HTML
        )
        return self.IN_MAIN_STATE

    def visualizeDevice(self, upd: Update, ctx: CallbackContext) -> int:
        if not upd.message:
            return self.IN_MAIN_STATE

        if len(ctx.args) != 1:
            upd.message.reply_text('Wrong number of arguments. Use /help to get more info')
            return self.IN_MAIN_STATE
        try:
            device = int(ctx.args[0])
        except:
            upd.message.reply_text('Wrong argument passed!')
            return self.IN_MAIN_STATE
        try:
            img = self.deviceManager.deviceGraphMeasurements(device)
            upd.message.reply_photo(img)
        except Exception as e:
            upd.message.reply_text('Failed to create graph. Exception: {0}'.format(e))
        return self.IN_MAIN_STATE

    def monitorDevice(self, upd: Update, ctx: CallbackContext) -> int:
        if not upd.message:
            return self.IN_MAIN_STATE

        if len(ctx.args) != 1:
            upd.message.reply_text('Wrong number of arguments. Use /help to get more info')
            return self.IN_MAIN_STATE
        try:
            device = int(ctx.args[0])
        except:
            upd.message.reply_text('Wrong argument passed!')
            return self.IN_MAIN_STATE

        schat = self.subscribedChats[upd.effective_chat.id]
        if device in schat.deviceList:
            self.subscribedChats[upd.effective_chat.id].removeDevice(device)
            upd.message.reply_text('You are not monitoring device#{0} anymore!'.format(device))
            return self.IN_MAIN_STATE

        self.subscribedChats[upd.effective_chat.id].appendDevice(device)
        upd.message.reply_text('You are now monitoring device#{0}!'.format(device))
        return self.IN_MAIN_STATE


    def broadcastMessageToChats(self, chatIds: List[int], msg: str) -> bool:
        assert len(chatIds) < 1e3, 'Too large user list, cannot run multithreaded message sending. Contact developers!'
        def sendMessage(chatId: int) -> bool:
            for i in range(self.SEND_MESSAGE_ATTEMPTS):
                try:
                    m: Message = self.updater.bot.send_message(chat_id, msg)
                    return True if m else False
                except Exception as e:
                    print('Exception raised when sending to chat_id={0} attempt#{2}:\n\t>>{1}'.format(chatId, str(e), i))
                    time.sleep(self.SEND_MESSAGE_REATTEMPT_DELAY)
            return False

        threads = []
        for chat_id in chatIds:
            thr = threading.Thread(target=sendMessage, args=(chat_id,))
            threads.append(thr)
            thr.start()

        for thr in threads:
            thr.join()

    def handlePacketReceived(self, packet: RemotePacket) -> None:
        ids = [schat.chat_id for schat in self.subscribedChats.values() if packet.remoteDevice in schat.deviceList]
        self.broadcastMessageToChats(ids, str(packet))