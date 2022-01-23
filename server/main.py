from botobj import TelegramBot
from serialMonitor import SerialMonitor, DebugMonitor
from fileLogger import FileLogger
from deviceManager import DeviceManager
import click, re

bot: TelegramBot | None = None
fLogger: FileLogger | None = None
deviceManager: DeviceManager | None = None

def handleSerialInput(msg: str):
    global bot, fLogger, deviceManager

    packet = deviceManager.handleMessageReceived(msg)

    if fLogger:
        fLogger.log(msg)

    print(msg)

    if bot:
        bot.handlePacketReceived(packet)

@click.command()
@click.option('-t', '--telegram-token', help='telegram bot token')
@click.option('-p', '--com-port', help='name of the serial port to start listening to; auto - to autodetect')
@click.option('-o', '--out-file', help='file for logging serial port')
@click.option('-b', '--bot-file', help='file for saving telegram bot state')
@click.option('-d', '--database-file', help='file for saving entries')
def main(telegram_token, com_port, out_file, bot_file, database_file):
    global bot, fLogger, deviceManager

    deviceManager = DeviceManager(database_file)

    # Initialize Telegram bot
    if telegram_token:
        bot = TelegramBot(telegram_token, bot_file, deviceManager)
        bot.startBot()
        print('> Telegram bot started!')
    else:
        print('> No telegram bot token provided! Bot has not been started!')

    # Initialize data obtainer
    data = DebugMonitor()
    # data: SerialMonitor = SerialMonitor()
    if com_port:
        data.setup(port=com_port)
        print('> {0} with comport {1} started!'.format(type(data).__name__, com_port))
    else:
        data.setup()
        print('> {0} without any comport started!'.format(type(data).__name__))

    # Initialize file logger
    if out_file:
        fLogger = FileLogger(out_file)
        print('> File logging started!')
    else:
        print('> No output file specified. No logging to file enabled')

    data.listen(handleSerialInput)
    bot.stopBot()

if __name__ == '__main__':
    main()