from botobj import TelegramBot
from serialMonitor import SerialMonitor, DebugMonitor, DataObtainer
from fileLogger import FileLogger
from deviceManager import DeviceManager
import click, re

MOISTENSOR_VERSION = '0.3'

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
@click.option('-b', '--bot-file', help='file for saving telegram bot state', default='tgbot.pickle')
@click.option('-d', '--database-file', help='file for saving entries', default='db.pickle')
@click.option('-m', '--monitor', type=click.Choice(['debug', 'serial'], case_sensitive=False), help='type of monitor to use', default='serial')
def main(telegram_token, com_port, out_file, bot_file, database_file, monitor):
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
    data: DataObtainer | None = None
    if monitor == 'serial':
        data: SerialMonitor = SerialMonitor()
    elif monitor == 'debug':
        data: DebugMonitor = DebugMonitor()
    else:
        raise Exception('Unknown monitor provided: {0}'.format(monitor))

    if com_port:
        data.setup(port=com_port)
    else:
        data.setup()
    print('> {0} with comport {1} started!'.format(type(data).__name__, data.port))

    # Initialize file logger
    if out_file:
        fLogger = FileLogger(out_file)
        print('> File logging started!')
    else:
        print('> No output file specified. No logging to file enabled')

    data.listen(handleSerialInput)
    bot.stopBot()

if __name__ == '__main__':
    print('Welcome to Moistensor v{0}'.format(MOISTENSOR_VERSION))
    main()