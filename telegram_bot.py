import logging

from environs import Env
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

logger = logging.getLogger('Logger quiz telegram bot')


def start(update, context):
    update.message.reply_text('Здравствуйте!')


def send_echo_message(update, context):
    update.message.reply_text(update.message.text)


if __name__ == '__main__':
    env = Env()
    env.read_env()

    telegram_bot_token = env.str('TELEGRAM_BOT_TOKEN')

    updater = Updater(telegram_bot_token)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))

    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, send_echo_message))

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )
    logger.setLevel(logging.INFO)

    updater.start_polling()
    updater.idle()
