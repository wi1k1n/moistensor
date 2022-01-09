from botobj import TelegramBot
from serialMonitor import SerialMonitor, DebugMonitor
from fileLogger import FileLogger
import click, re

bot: TelegramBot = None
fLogger: FileLogger = None

def handleSerialInput(msg: str):
    if fLogger:
        fLogger.log(msg)

    print(msg)

    if bot:
        preambule = re.search('\[D\d+PRv\d+-\d+\]', msg)
        if preambule:
            preambuleStr = preambule.group()
            body = msg[preambule.start() + len(preambuleStr):]

            msgDict = {
                'device': int(re.search('D\d+', preambuleStr).group()[1:]),
                'protVers': int(re.search('PRv\d+', preambuleStr).group()[3:]),
                'packetType': int(re.search('-\d+\]', preambuleStr).group()[1:-1]),
            }
            if msgDict['packetType'] == 1:  # measurement transmission
                timeSpan = re.search('t\d+(h|m)', body).group()
                msgDict['body'] = {
                    'voltage': re.search('v(\d+|\?)', body).group()[1:],
                    'timeSpan': int(timeSpan[1:-1]) * (1 if timeSpan[-1] == 'm' else 60),
                    'measurement': int(re.search('m\d+', body).group()[1:])
                }
            elif msgDict['packetType'] == 2:  # calibration update
                timeSpan = re.search('t\d+(h|m)', body).group()
                msgDict['body'] = {
                    'voltage': re.search('v(\d+|\?)', body).group()[1:],
                    'timeSpan': int(timeSpan[1:-1]) * (1 if timeSpan[-1] == 'm' else 60),
                    'voltageMin': re.search('vn(\d+|\?)', body).group()[2:],
                    'voltageMax': re.search('vx(\d+|\?)', body).group()[2:],
                    'calibrDry': int(re.search('cd\d+', body).group()[2:]),
                    'calibrWet': int(re.search('cw\d+', body).group()[2:]),
                    'intervalIdx': int(re.search('idx\d+', body).group()[3:]),
                    'interval': int(re.search('int\d+', body).group()[3:]),
                    'first': bool(re.search('f\d', body).group()[1:]),
                }
        else:
            print('[ERROR Invalid Entry]: ' + msg)
            msgDict = {'error': msg}

        bot.handleSerialUpdate(msgDict)

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
    # data = DebugMonitor()
    data: SerialMonitor = SerialMonitor()
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
    bot.foreground()

if __name__ == '__main__':
    main()