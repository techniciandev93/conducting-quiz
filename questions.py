import os


def split_questions(questions_text):
    part_questions = {}
    split_text_questions = questions_text.split('\n\n')
    total_questions = len(split_text_questions)
    for nom, question in enumerate(split_text_questions):
        if nom + 1 < total_questions:
            answer = split_text_questions[nom + 1]
            if question.startswith('Вопрос') and answer.startswith('Ответ'):
                part_questions[question.split(':')[-1].strip()] = answer.split(':')[-1].strip()
    return part_questions


def read_questions_files(folder_path):
    questions = {}
    for root, directories, files in os.walk(folder_path):
        for file in files:
            with open(os.path.join(root, file), 'r', encoding='KOI8-R') as question_file:
                questions.update(split_questions(question_file.read()))
    return questions
