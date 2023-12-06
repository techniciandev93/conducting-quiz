import os


def split_questions(questions_text):
    part_questions = []
    split_text_questions = questions_text.split('\n\n')
    for nom in range(len(split_text_questions)):
        try:
            if 'Вопрос' in split_text_questions[nom] and 'Ответ' in split_text_questions[nom+1]:
                part_questions.append({
                    'questions': split_text_questions[nom].split(':')[-1],
                    'answer': split_text_questions[nom+1].split(':')[-1]
                })
        except IndexError:
            pass
    return part_questions


def read_questions_files(folder_path):
    questions = []
    for root, directories, files in os.walk(folder_path):
        for file in files:
            with open(os.path.join(root, file), 'r', encoding='KOI8-R') as question_file:
                questions.extend(split_questions(question_file.read()))
    return questions


if __name__ == '__main__':
    questions_path = 'quiz-questions/'
    a = read_questions_files(questions_path)
