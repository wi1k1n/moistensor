from serialMonitor import SerialMonitor, DebugMonitor, DataObtainer
from fileLogger import FileLogger
from deviceManager import DeviceManager
import click, re

MOISTENSOR_VERSION = '1.0'

@click.command()
@click.option('--telegram-token', help='telegram bot token')
@click.option('--com-port', help='name of the serial port to start listening to; auto - to autodetect')
@click.option('--log-file', help='file for logging serial port')
@click.option('--bot-file', help='file for saving telegram bot state', default='tgbot.pickle')
@click.option('--database-file', help='file for saving entries', default='db.pickle')
@click.option('--monitor', type=click.Choice(['debug', 'serial'], case_sensitive=False), help='type of monitor to use', default='serial')
@click.option('--mqtt-host', help='ip address of the MQTT  broker', default='127.0.0.1')
@click.option('--mqtt-port', help='port of the MQTT broker', type=int, default='1883')
@click.option('--mqtt-user', help='username to login to the MQTT broker')
@click.option('--mqtt-passwd', help='password to login to the MQTT broker')
@click.option('--mqtt-topic', help='topic to publish data to', default='homeassistant/sensor/HA_OBJECT_ID')
def main(telegram_token, com_port, log_file, bot_file, database_file, monitor, mqtt_host, mqtt_port, mqtt_user, mqtt_passwd, mqtt_topic):
    deviceManager: DeviceManager = DeviceManager(database_file)

    # Initialize Telegram bot
    bot = None
    if telegram_token:
        from botobj import TelegramBot
        bot: TelegramBot = TelegramBot(telegram_token, bot_file, deviceManager)
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
        print('> {0} with comport {1} started!'.format(type(data).__name__, data.port))
    else:
        data.setup()
        print('> {0} started!'.format(type(data).__name__))

    # Initialize MQTT Bridge
    mqttBridge = None
    if all([mqtt_host, mqtt_port, mqtt_topic, all([mqtt_user, mqtt_passwd]) if any([mqtt_user, mqtt_passwd]) else True]):
        from mqttBridge import MQTTBridge
        mqttBridge: MQTTBridge = MQTTBridge(mqtt_host, mqtt_port, mqtt_topic, mqtt_user, mqtt_passwd)
        mqttBridge.openBridge()
    print('> MQTT Bridge started at host {0}:{1}{2}'.format(mqtt_host, mqtt_port, ' with user {0}'.format(mqtt_user) if mqtt_user else '')
          if mqttBridge else 'MQTT Bridge was not started!')

    # Initialize file logger
    fLogger = None
    if log_file:
        fLogger: FileLogger = FileLogger(log_file)
        print('> File logging started!')
    else:
        print('> No output file specified. No logging to file enabled')

    def handleSerialInput(msg: str):
        print(msg)
        if fLogger:
            fLogger.log(msg)

        packet = deviceManager.handleMessageReceived(msg)

        if bot:
            bot.handlePacketReceived(packet)
        if mqttBridge:
            mqttBridge.handlePacketReceived(packet)
    data.listen(handleSerialInput)

    if bot:
        bot.stopBot()
    if mqttBridge:
        mqttBridge.closeBridge()

if __name__ == '__main__':
    print('Welcome to Moistensor v{0}'.format(MOISTENSOR_VERSION))
    main()