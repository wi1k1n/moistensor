import logging
from typing import Dict
from telegram import Update, User
from telegram.ext import (
    Updater,
    Dispatcher,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    PicklePersistence
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, _token: str):
        self.TOKEN = _token
        self.WAITING_FOR_PASSWORD,\
            self.STREAMEVENTS,\
            self.IGNORE = range(3)

        self.INITIAL_ATTEMPTS = 4

        self.updater: Updater = None
        self.dispatcher: Dispatcher = None

        self.authorizedUserIds = []
        self.subscribedChatIds = []
        self.ready = False

    def startBot(self, blockThread = False) -> None:
        """Run the bot."""
        # TODO: add persistence

        # Create the Updater and pass it your bot's token.
        self.updater = Updater(self.TOKEN)

        # Get the dispatcher to register handlers
        self.dispatcher = self.updater.dispatcher

        # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                self.WAITING_FOR_PASSWORD: [
                    MessageHandler(Filters.text, self.checkPassCode),
                ],
                self.STREAMEVENTS: [
                    MessageHandler(Filters.text, self.streamEvents),
                ],
                self.IGNORE: []
            },
            fallbacks=[],
        )

        self.dispatcher.add_handler(conv_handler)

        # Start the Bot
        self.updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        if blockThread:
            self.updater.idle()

    def facts_to_str(self, user_data: Dict[str, str]) -> str:
        """Helper function for formatting the gathered user info."""
        facts = [f'{key} - {value}' for key, value in user_data.items()]
        return "\n".join(facts).join(['\n', '\n'])

    def generatePassCode(self, usr: User) -> str:
        return 'TODO:' + str(usr.id)

    def start(self, upd: Update, ctx: CallbackContext) -> int:
        if upd.effective_user.is_bot:
            return self.IGNORE
        upd.message.reply_text(
            "Welcome to Moistensor Bot. Please authorize yourself with a code from the console."
        )
        passCode = self.generatePassCode(upd.effective_user)
        ctx.user_data['passCode'] = passCode
        ctx.user_data['authAttempts'] = self.INITIAL_ATTEMPTS
        ctx.user_data['banned'] = False
        print('New user: [' + str(upd.effective_user.id) + '] ' + upd.effective_user.name + ' | Passcode: ' + passCode)
        return self.WAITING_FOR_PASSWORD

    def alarm(ctx: CallbackContext) -> None:
        """Send the alarm message."""
        ctx.bot.send_message(ctx.job.context, text='Beep!')

    def checkPassCode(self, upd: Update, ctx: CallbackContext) -> int:
        if upd.message.text != ctx.user_data['passCode']:
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
        upd.message.reply_text(
            'Successfully authorized! Listening for the events.'
        )
        self.authorizedUserIds.append(upd.effective_user.id)
        self.subscribedChatIds.append(upd.message.chat_id)

        return self.STREAMEVENTS

    def streamEvents(self, upd: Update, ctx: CallbackContext) -> int:
        upd.message.reply_text(
            'Waiting for events to stream'
        )
        return self.STREAMEVENTS

    def regular_choice(self, update: Update, context: CallbackContext) -> int:
        """Ask the user for info about the selected predefined choice."""
        text = update.message.text
        context.user_data['choice'] = text
        update.message.reply_text(f'Your {text.lower()}? Yes, I would love to hear about that!')

        return self.TYPING_REPLY

    def custom_choice(self, update: Update, context: CallbackContext) -> int:
        """Ask the user for a description of a custom category."""
        update.message.reply_text(
            'Alright, please send me the category first, for example "Most impressive skill"'
        )

        return self.TYPING_CHOICE

    def received_information(self, update: Update, context: CallbackContext) -> int:
        """Store info provided by user and ask for the next category."""
        user_data = context.user_data
        text = update.message.text
        category = user_data['choice']
        user_data[category] = text
        del user_data['choice']

        update.message.reply_text(
            "Neat! Just so you know, this is what you already told me:"
            f"{self.facts_to_str(user_data)} You can tell me more, or change your opinion"
            " on something."
        )

        return self.CHOOSING

    def done(self, update: Update, context: CallbackContext) -> int:
        """Display the gathered info and end the conversation."""
        user_data = context.user_data
        if 'choice' in user_data:
            del user_data['choice']

        update.message.reply_text(
            f"I learned these facts about you: {self.facts_to_str(user_data)}Until next time!"
        )

        user_data.clear()
        return ConversationHandler.END

    def sendMessage(self, msg: str) -> None:
        for chatId in self.subscribedChatIds:
            self.updater.bot.send_message(chatId, msg)