import argparse
import logging
import random
import re

import redis
import vk_api as vk
from environs import Env
from fuzzywuzzy import fuzz
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType

from questions import read_questions_files

logger = logging.getLogger('Logger  vk bot')


def build_keyboard_menu():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('Мой счёт')
    return keyboard


def send_message_vk(event, vk_api, message):
    keyboard = build_keyboard_menu()
    vk_api.messages.send(
        user_id=event.user_id,
        message=message,
        random_id=random.randint(1, 1000),
        keyboard=keyboard.get_keyboard(),
    )


def processing_vk_quiz(event, vk_api, questions, redis_connection):
    question = redis_connection.get(event.user_id)
    if question:
        question = question.decode()

    if event.text == 'Новый вопрос':
        if question:
            message = f'Вы должны ответить на вопрос: {question}'
            send_message_vk(event, vk_api, message)
        else:
            question = random.choice(tuple(questions.keys()))
            redis_connection.set(event.user_id, question)
            send_message_vk(event, vk_api, question)

    elif event.text == 'Сдаться':
        if question:
            answer = questions[question]
            message = f'Вот тебе правильный ответ: {answer}'
            send_message_vk(event, vk_api, message)
            redis_connection.delete(event.user_id)

            send_message_vk(event, vk_api, '\nНовый вопрос')
            question = random.choice(tuple(questions.keys()))
            redis_connection.set(event.user_id, question)
            send_message_vk(event, vk_api, question)
        else:
            message = 'Вы ещё не запрашивали вопрос.\nДля запроса вопроса нажми "Новый вопрос"'
            send_message_vk(event, vk_api, message)

    else:
        if not question:
            message = 'Для запроса вопроса нажми "Новый вопрос"'
            send_message_vk(event, vk_api, message)
        else:
            answer = re.split(r'[.(]', questions[question].replace('...', ''))[0].lower().strip()
            user_answer = event.text.lower().strip()
            ratio = fuzz.token_sort_ratio(answer, user_answer)

            if ratio >= 80:
                message = 'Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»'
                send_message_vk(event, vk_api, message)
                redis_connection.delete(event.user_id)
            else:
                message = 'Неправильно… Попробуешь ещё раз?'
                send_message_vk(event, vk_api, message)


if __name__ == "__main__":
    try:
        env = Env()
        env.read_env()
        vk_group_token = env.str('VK_GROUP_TOKEN')
        redis_url = env.str('REDIS_URL')
        redis_port = env.str('REDIS_PORT')
        redis_password = env.str('REDIS_PASSWORD')

        redis_connection = redis.Redis(host=redis_url, port=redis_port, password=redis_password)

        parser = argparse.ArgumentParser(description='Этот скрипт запускает бота викторин для ВК '
                                                     'по умолчанию без аргументов будет взят путь из корня проекта '
                                                     'к каталогу quiz-questions/: python vk_bot.py')
        parser.add_argument('--path', type=str, help='Укажите путь к каталогу с вопросами',
                            nargs='?', default='quiz-questions/')
        args = parser.parse_args()
        questions = read_questions_files(args.path)

        vk_session = vk.VkApi(token=vk_group_token)
        vk_api = vk_session.get_api()
        longpoll = VkLongPoll(vk_session)

        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
        )
        logger.setLevel(logging.INFO)
        logger.info('Бот ВК запущен')

        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                processing_vk_quiz(event, vk_api, questions, redis_connection)
    except Exception as error:
        logger.exception(error)
