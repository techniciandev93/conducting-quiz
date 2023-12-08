import logging
import random
import re

import redis
from environs import Env
from fuzzywuzzy import fuzz
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler

from main import read_questions_files


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


def handle_text(update, context):
    question = connection_redis.get(update.message.from_user.id)
    if question:
        question = question.decode()

    if update.message.text == 'Новый вопрос':
        if question:
            update.message.reply_text(f'Вы должны ответить на вопрос: {question}')
        else:
            question = random.choice(tuple(questions.keys()))
            connection_redis.set(update.message.from_user.id, question)
            update.message.reply_text(question)

    elif update.message.text == 'Сдаться':
        if question:
            answer = questions[question]
            update.message.reply_text(f'Вот тебе правильный ответ: {answer}')
            connection_redis.delete(update.message.from_user.id)
        else:
            update.message.reply_text('Вы ещё не запрашивали вопрос.\nДля запроса вопроса нажми "Новый вопрос"')

    else:
        if not question:
            update.message.reply_text('Для запроса вопроса нажми "Новый вопрос"')
        else:
            answer = re.split(r'[.(]', questions[question].replace('...', ''))[0].lower().strip()
            user_answer = update.message.text.lower().strip()
            ratio = fuzz.token_sort_ratio(answer, user_answer)

            if ratio >= 80:
                update.message.reply_text('Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»')
                connection_redis.delete(update.message.from_user.id)
            else:
                update.message.reply_text('Неправильно… Попробуешь ещё раз?')


def handle_new_question_request(update, context):
    question = connection_redis.get(update.message.from_user.id)
    if question:
        update.message.reply_text(f'Вы должны ответить на вопрос: {question.decode()}')
        return ANSWER_QUESTION
    else:
        question = random.choice(tuple(questions.keys()))
        connection_redis.set(update.message.from_user.id, question)
        update.message.reply_text(question)
        return ANSWER_QUESTION


def handle_solution_attempt(update, context):
    question = connection_redis.get(update.message.from_user.id)
    if not question:
        update.message.reply_text('Для запроса вопроса нажми "Новый вопрос"')
        return QUESTION
    else:
        answer = re.split(r'[.(]', questions[question.decode()].replace('...', ''))[0].lower().strip()
        user_answer = update.message.text.lower().strip()
        ratio = fuzz.token_sort_ratio(answer, user_answer)

        if ratio >= 80:
            update.message.reply_text('Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»')
            connection_redis.delete(update.message.from_user.id)
            return QUESTION
        else:
            update.message.reply_text('Неправильно… Попробуешь ещё раз?')
            return QUESTION


def handler_give_up(update, context):
    question = connection_redis.get(update.message.from_user.id)
    answer = questions[question.decode()]
    update.message.reply_text(f'Вот тебе правильный ответ: {answer}')
    connection_redis.delete(update.message.from_user.id)
    return ConversationHandler.END


if __name__ == '__main__':
    env = Env()
    env.read_env()

    telegram_bot_token = env.str('TELEGRAM_BOT_TOKEN')
    redis_url = env.str('REDIS_URL')
    redis_port = env.str('REDIS_PORT')
    redis_password = env.str('REDIS_PASSWORD')

    questions_path = 'quiz-questions/'
    questions = read_questions_files(questions_path)
    updater = Updater(telegram_bot_token)
    connection_redis = redis.Redis(host=redis_url, port=redis_port, password=redis_password)
    connection_redis.ping()

    dispatcher = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            QUESTION: [MessageHandler(Filters.regex('^Новый вопрос$'), handle_new_question_request)],
            ANSWER_QUESTION: [MessageHandler(Filters.text & ~Filters.command, handle_solution_attempt)],
        },
        fallbacks=[MessageHandler(Filters.regex('^Сдаться$'), handler_give_up)],
    )
    dispatcher.add_handler(conv_handler)


    #dispatcher.add_handler(CommandHandler('start', start))
    #dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )
    logger.setLevel(logging.INFO)

    updater.start_polling()
    updater.idle()
