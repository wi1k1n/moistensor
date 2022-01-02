import logging
from typing import Dict
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext
)

class TelegramBot:
    def __init__(self, _token: str):
        self.TOKEN = _token

        # Enable logging
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)

        self.CHOOSING, self.TYPING_REPLY, self.TYPING_CHOICE = range(3)

        self.reply_keyboard = [
            ['Age', 'Favourite colour'],
            ['Number of siblings', 'Something else...'],
            ['Done'],
        ]

    def startBot(self) -> None:
        """Run the bot."""
        # Create the Updater and pass it your bot's token.
        updater = Updater(self.TOKEN)

        # Get the dispatcher to register handlers
        dispatcher = updater.dispatcher

        # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                self.CHOOSING: [
                    MessageHandler(
                        Filters.regex('^(Age|Favourite colour|Number of siblings)$'), self.regular_choice
                    ),
                    MessageHandler(Filters.regex('^Something else...$'), self.custom_choice),
                ],
                self.TYPING_CHOICE: [
                    MessageHandler(
                        Filters.text & ~(Filters.command | Filters.regex('^Done$')), self.regular_choice
                    )
                ],
                self.TYPING_REPLY: [
                    MessageHandler(
                        Filters.text & ~(Filters.command | Filters.regex('^Done$')),
                        self.received_information,
                    )
                ],
            },
            fallbacks=[MessageHandler(Filters.regex('^Done$'), self.done)],
        )

        dispatcher.add_handler(conv_handler)

        # Start the Bot
        updater.start_polling()

        # # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # # SIGTERM or SIGABRT. This should be used most of the time, since
        # # start_polling() is non-blocking and will stop the bot gracefully.
        # updater.idle()

    def facts_to_str(self, user_data: Dict[str, str]) -> str:
        """Helper function for formatting the gathered user info."""
        facts = [f'{key} - {value}' for key, value in user_data.items()]
        return "\n".join(facts).join(['\n', '\n'])

    def start(self, update: Update, context: CallbackContext) -> int:
        """Start the conversation and ask user for input."""
        update.message.reply_text(
            "Hi! My name is Doctor Botter. I will hold a more complex conversation with you. "
            "Why don't you tell me something about yourself?"
        )

        return self.CHOOSING

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
        pass