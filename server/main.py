from botobj import TelegramBot
from serialMonitor import SerialMonitor, DebugMonitor
from fileLogger import FileLogger
from protocolHandler import parseMessage
import click, re

bot: TelegramBot = None
fLogger: FileLogger = None

def handleSerialInput(msg: str):
    global bot, fLogger

    if fLogger:
        fLogger.log(msg)

    print(msg)

    if bot:
        packet = parseMessage(msg)
        bot.handleSerialUpdate(packet)

@click.command()
@click.option('-t', '--telegram-token', help='telegram bot token')
@click.option('-p', '--com-port', help='name of the serial port to start listening to; auto - to autodetect')
@click.option('-o', '--out-file', help='file for logging serial port')
def main(telegram_token, com_port, out_file):
    global bot, fLogger
    # Initialize Telegram bot
    if telegram_token:
        bot = TelegramBot(telegram_token)
        bot.startBot()
    else:
        print('No telegram bot token provided! Bot has not been started!')

    # Initialize monitor
    data = DebugMonitor()
    # data: SerialMonitor = SerialMonitor()
    if com_port:
        data.setup(port=com_port)
    else:
        data.setup()

    # Initialize file logger
    if out_file:
        fLogger = FileLogger(out_file)
    else:
        print('No output file specified. No logging to file enabled')

    data.listen(handleSerialInput)
    bot.stopBot()

if __name__ == '__main__':
    main()