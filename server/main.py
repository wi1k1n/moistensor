from botobj import TelegramBot
from serialMonitor import SerialMonitor, DebugMonitor
from config import TELEGRAMBOT_API

if __name__ == '__main__':
    bot = TelegramBot(TELEGRAMBOT_API)
    bot.startBot()

    # data = SerialMonitor()
    data = DebugMonitor()
    data.setup()

    def log(str):
        print(str)
        bot.sendMessage(str)

    data.listen(log)