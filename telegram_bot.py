import argparse
import logging
import random
import re
from functools import partial

import redis
from environs import Env
from fuzzywuzzy import fuzz
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

from questions import read_questions_files


logger = logging.getLogger('Logger quiz telegram bot')

QUESTION, ANSWER_QUESTION = range(2)


def build_keyboard_menu():
    button_list = [
        ['Новый вопрос', 'Сдаться'],
        ['Мой счёт']
    ]
    reply_markup = ReplyKeyboardMarkup(button_list)
    return reply_markup


def start(update, context):
    reply_markup = build_keyboard_menu()
    update.message.reply_text('Здравствуйте! Это бот викторин', reply_markup=reply_markup)
    return QUESTION


def handle_new_question_request(update, context, redis_connection, questions):
    question = redis_connection.get(update.message.from_user.id)
    if question:
        update.message.reply_text(f'Вы должны ответить на вопрос: {question.decode()}')
    else:
        question = random.choice(tuple(questions.keys()))
        redis_connection.set(update.message.from_user.id, question)
        update.message.reply_text(question)
    return ANSWER_QUESTION


def handle_solution_attempt(update, context, redis_connection, questions):
    question = redis_connection.get(update.message.from_user.id)
    answer = re.split(r'[.(]', questions[question.decode()].replace('...', ''))[0].lower().strip()
    user_answer = update.message.text.lower().strip()
    ratio = fuzz.token_sort_ratio(answer, user_answer)

    if ratio >= 80:
        update.message.reply_text('Правильно! Поздравляю! Вот тебе следующий вопрос.')
        redis_connection.delete(update.message.from_user.id)
        return handle_new_question_request(update, context, redis_connection)

    update.message.reply_text('Неправильно… Попробуешь ещё раз?')
    return ANSWER_QUESTION


def handler_give_up(update, context, redis_connection, questions):
    question = redis_connection.get(update.message.from_user.id)
    answer = questions[question.decode()]
    update.message.reply_text(f'Вот тебе правильный ответ: {answer}')
    redis_connection.delete(update.message.from_user.id)
    update.message.reply_text(f'\nНовый вопрос')
    handle_new_question_request(update, context, redis_connection)


if __name__ == '__main__':
    try:
        env = Env()
        env.read_env()

        telegram_bot_token = env.str('TELEGRAM_BOT_TOKEN')
        redis_url = env.str('REDIS_URL')
        redis_port = env.str('REDIS_PORT')
        redis_password = env.str('REDIS_PASSWORD')

        parser = argparse.ArgumentParser(description='Этот скрипт запускает бота викторин для телеграм '
                                                     'по умолчанию без аргументов будет взят путь из корня проекта '
                                                     'к каталогу quiz-questions/: python telegram_bot.py')
        parser.add_argument('--path', type=str, help='Укажите путь к каталогу с вопросами',
                            nargs='?', default='quiz-questions/')
        args = parser.parse_args()

        questions = read_questions_files(args.path)
        updater = Updater(telegram_bot_token)
        redis_connection = redis.Redis(host=redis_url, port=redis_port, password=redis_password)

        handle_new_question_request_with_args = partial(handle_new_question_request,
                                                        redis_connection=redis_connection,
                                                        questions=questions)

        handle_solution_attempt_with_args = partial(handle_solution_attempt,
                                                    redis_connection=redis_connection, questions=questions)

        handler_give_up_with_args = partial(handler_give_up,
                                            redis_connection=redis_connection,
                                            questions=questions)

        dispatcher = updater.dispatcher
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                QUESTION: [MessageHandler(Filters.regex('^Новый вопрос$'), handle_new_question_request_with_args)],
                ANSWER_QUESTION: [
                    MessageHandler(Filters.regex('^Сдаться$'), handler_give_up_with_args),
                    MessageHandler(Filters.regex('^Новый вопрос$'), handle_new_question_request_with_args),
                    MessageHandler(Filters.text & ~Filters.command, handle_solution_attempt_with_args)]
            },
            fallbacks=[],
        )
        dispatcher.add_handler(conv_handler)

        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
        )
        logger.setLevel(logging.INFO)
        logger.info('Бот телеграмм запущен')

        updater.start_polling()
        updater.idle()
    except Exception as error:
        logger.exception(error)
