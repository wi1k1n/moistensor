import logging, hashlib, random, secrets, threading
import time
from typing import Dict, List, Set
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
)
from remoteDevice import RemoteDevice

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

class TelegramBot:
    def __init__(self, _token: str):
        self.TOKEN: str = _token
        self.WAITING_FOR_PASSWORD,\
            self.STREAMEVENTS,\
            self.IGNORE = range(3)

        self.AUTH_INITIAL_ATTEMPTS = 4
        self.SEND_MESSAGE_ATTEMPTS = 3
        self.SEND_MESSAGE_REATTEMT_DELAY = 0.5  # in seconds

        self.updater: Updater = None
        self.dispatcher: Dispatcher = None

        self.authorizedUsers: Dict[int, TGUser] = dict()
        self.subscribedChats: Dict[int, SubscribedChat] = dict()
        self.devices: Dict[int, RemoteDevice] = dict()

    def startBot(self, blockThread = False) -> None:
        """Run the bot."""
        # TODO: add persistence
        self.updater = Updater(self.TOKEN)
        self.dispatcher = self.updater.dispatcher
        self.dispatcher.add_handler(ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                self.WAITING_FOR_PASSWORD: [
                    CommandHandler('start', self.start),
                    MessageHandler(Filters.text, self.checkPassCode),
                ],
                self.STREAMEVENTS: [
                    MessageHandler(Filters.text, self.streamEvents),
                ],
                self.IGNORE: []
            },
            fallbacks=[],
        ))
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
        if upd.effective_user.is_bot:
            return self.IGNORE
        if upd.effective_user.id in self.authorizedUsers:
            upd.message.reply_text('You are already authorized. Try /help command.')
            return
        if upd.effective_chat.type != 'private':
            return

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

        return self.STREAMEVENTS

    def streamEvents(self, upd: Update, ctx: CallbackContext) -> int:
        upd.message.reply_text(
            'Waiting for events to stream'
        )
        return self.STREAMEVENTS

    def broadcastMessageToChats(self, chatIds: List[int], msg: str) -> bool:
        assert len(chatIds) < 1e3, 'Too large user list, cannot run multithreaded message sending. Contact developers!'
        def sendMessage(chatId: int) -> bool:
            for i in range(self.SEND_MESSAGE_ATTEMPTS):
                try:
                    m: Message = self.updater.bot.send_message(chat_id, msg)
                    return True if m else False
                except Exception as e:
                    print('Exception raised when sending to chat_id={0} attempt#{2}:\n\t>>{1}'.format(chatId, str(e), i))
                    time.sleep(self.SEND_MESSAGE_REATTEMT_DELAY)
            return False

        threads = []
        for chat_id in chatIds:
            thr = threading.Thread(target=sendMessage, args=(chat_id,))
            threads.append(thr)
            thr.start()

        for thr in threads:
            thr.join()

    def broadcastMessageToSubscribers(self, msg: str) -> None:
        self.broadcastMessageToChats(list(self.subscribedChats.keys()), msg)

    def handleSerialUpdate(self, msg: dict) -> None:
        if not msg:
            return
        if 'error' in msg:
            self.broadcastMessageToSubscribers(str(msg))
            return

        deviceID: int = msg['device']
        if not (deviceID in self.devices):
            self.devices[deviceID] = RemoteDevice(deviceID)
        body = msg['body']
        if msg['packetType'] == 1:  # measurement transmission
            self.devices[deviceID].updateMeasurement(body['voltage'], body['timeSpan'], body['measurement'])
        elif msg['packetType'] == 2:  # update calibrations
            self.devices[deviceID].updateCalibrations(body['voltage'], body['timeSpan'], body['voltageMin'],
                                                      body['voltageMax'], body['calibrDry'], body['calibrWet'],
                                                      body['intervalIdx'], body['interval'])
        self.broadcastMessageToSubscribers(str(msg))