import os


def split_questions(questions_text):
    part_questions = {}
    split_text_questions = questions_text.split('\n\n')
    for nom in range(len(split_text_questions)):
        if split_text_questions[nom].startswith('Вопрос') and split_text_questions[nom+1].startswith('Ответ'):
            part_questions[split_text_questions[nom].split(':')[-1]] = split_text_questions[nom+1].split(':')[-1]
    return part_questions


def read_questions_files(folder_path):
    questions = {}
    for root, directories, files in os.walk(folder_path):
        for file in files:
            with open(os.path.join(root, file), 'r', encoding='KOI8-R') as question_file:
                questions.update(split_questions(question_file.read()))
    return questions
