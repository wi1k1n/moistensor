from botobj import TelegramBot
from serialMonitor import SerialMonitor, DebugMonitor
from fileLogger import FileLogger
import click

@click.command()
@click.option('-t', '--telegram-token', help='telegram bot token')
@click.option('-p', '--com-port', help='name of the serial port to start listening to; auto - to autodetect')
@click.option('-o', '--out-file', help='file for logging serial port')
def main(telegram_token, com_port, out_file):
    bot: TelegramBot = None
    if telegram_token:
        bot = TelegramBot(telegram_token)
        bot.startBot()
    else:
        print('No telegram bot token provided! Bot has not been started!')

    data: SerialMonitor = SerialMonitor()
    # data = DebugMonitor()
    if com_port:
        data.setup(port=com_port)
    else:
        data.setup()

    fLogger: FileLogger = None
    if out_file:
        FileLogger(out_file)
    else:
        print('No output file specified. No logging to file enabled')

    def log(msg: str):
        print(msg)
        if bot:
            bot.sendMessage(msg)
        if fLogger:
            fLogger.log(msg)

    data.listen(log)

if __name__ == '__main__':
    main()