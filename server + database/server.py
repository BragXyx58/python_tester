import socket
import pyodbc
import jsonpickle
import hashlib

HOST = '127.0.0.1'
PORT = 4000

conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\SQLEXPRESS;DATABASE=TestSystem;Trusted_Connection=yes;'
db = pyodbc.connect(conn_str)
cursor = db.cursor()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
def log_action(user_id, table_name, action_type):
    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO Logs (user_id, table_name, action_type) VALUES (?, ?, ?)",
            user_id, table_name, action_type
        )
        db.commit()
def register_user(data):
    with db.cursor() as cursor:
        cursor.execute("SELECT id FROM Users WHERE username = ?", data['username'])
        if cursor.fetchone():
            return {'status': 'error', 'message': 'Пользователь уже существует'}
        cursor.execute("INSERT INTO Users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                       data['username'], hash_password(data['password']), data.get('is_admin', 0))
        db.commit()
        cursor.execute("SELECT id FROM Users WHERE username = ?", data['username'])
        user_id = cursor.fetchone().id
        log_action(user_id, 'Users', 'register')
        return {'status': 'ok', 'message': 'Регистрация успешна'}


def login_user(data):
    with db.cursor() as cursor:
        cursor.execute("SELECT id, is_admin FROM Users WHERE username = ? AND password_hash = ?",
                       data['username'], hash_password(data['password']))
        user = cursor.fetchone()
        if user:
            log_action(user.id, 'Users', 'login_admin' if user.is_admin else 'login')
            return {'status': 'ok', 'user_id': user.id, 'is_admin': bool(user.is_admin)}
        return {'status': 'error', 'message': 'Неверный логин или пароль'}

def get_tests():
    with db.cursor() as cursor:
        cursor.execute("SELECT id, title, description FROM Tests")
        return [{'id': row.id, 'title': row.title, 'description': row.description} for row in cursor.fetchall()]

def get_test_questions(test_id):
    with db.cursor() as cursor:
        cursor.execute("SELECT id, question_text FROM Questions WHERE test_id = ?", test_id)
        questions = []
        for row in cursor.fetchall():
            cursor.execute("SELECT id, answer_text FROM Answers WHERE question_id = ?", row.id)
            answers = [{'id': a.id, 'text': a.answer_text} for a in cursor.fetchall()]
            questions.append({'id': row.id, 'text': row.question_text, 'answers': answers})
        return {'questions': questions}

def get_answers_for_question(question_id):
    with db.cursor() as cursor:
        cursor.execute("SELECT id, answer_text, is_correct FROM Answers WHERE question_id = ?", question_id)
        answers = [{'id': row.id, 'text': row.answer_text, 'is_correct': row.is_correct} for row in cursor.fetchall()]
    return answers


def handle_get_answers(data):
    question_id = data.get('question_id')
    if not question_id:
        return {'status': 'error', 'message': 'Missing question_id'}

    with db.cursor() as cursor:
        cursor.execute("SELECT test_id FROM Questions WHERE id = ?", question_id)
        row = cursor.fetchone()
        test_id = row.test_id if row else None
        cursor.execute("SELECT id, answer_text, is_correct FROM Answers WHERE question_id = ?", question_id)
        answers = [{'id': r.id, 'text': r.answer_text, 'is_correct': r.is_correct} for r in cursor.fetchall()]

    return {'status': 'ok', 'answers': answers, 'test_id': test_id}


def submit_answers(data):
    correct = 0
    total = len(data['answers'])
    user_id = data['user_id']
    test_id = data['test_id']

    with db.cursor() as cursor:
        for item in data['answers']:
            qid = item['question_id']
            aid = item['answer_id']
            cursor.execute("SELECT is_correct FROM Answers WHERE id = ?", aid)
            is_correct = cursor.fetchone()
            if is_correct and is_correct[0]:
                correct += 1
            cursor.execute("INSERT INTO AnswerLogs (user_id, test_id, question_id, selected_answer_id, is_correct) VALUES (?, ?, ?, ?, ?)",
                           user_id, test_id, qid, aid, is_correct[0] if is_correct else 0)

        percent = round((correct / total) * 100, 2)
        cursor.execute("INSERT INTO Results (user_id, test_id, correct_answers, total_questions, score_percent) VALUES (?, ?, ?, ?, ?)",
                       user_id, test_id, correct, total, percent)
        db.commit()

    return {'status': 'ok', 'correct': correct, 'total': total, 'percent': percent}

def handle_admin_add_test(data):
    with db.cursor() as cursor:
        cursor.execute("INSERT INTO Tests (title, description) VALUES (?, ?)", data['title'], data.get('description', ''))
        db.commit()
        return {'status': 'ok', 'message': 'Тест добавлен'}

def handle_admin_add_question(data):
    with db.cursor() as cursor:
        cursor.execute("INSERT INTO Questions (test_id, question_text) VALUES (?, ?)", data['test_id'], data['text'])
        db.commit()
        return {'status': 'ok', 'message': 'Вопрос добавлен'}

def handle_admin_add_answer(data):
    with db.cursor() as cursor:
        cursor.execute("INSERT INTO Answers (question_id, answer_text, is_correct) VALUES (?, ?, ?)",
                       data['question_id'], data['text'], data['is_correct'])
        db.commit()
        return {'status': 'ok', 'message': 'Ответ добавлен'}

def handle_admin_statistics():
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT u.username, t.title, r.result_date, r.score_percent
            FROM Results r
            JOIN Users u ON u.id = r.user_id
            JOIN Tests t ON t.id = r.test_id
        """)
        return [{'user': row.username, 'test': row.title, 'date': str(row.result_date), 'score': row.score_percent}
                for row in cursor.fetchall()]
def handle_delete_question(data):
    question_id = data.get('question_id')
    if not question_id:
        return {'status': 'error', 'message': 'question_id is required'}

    with db.cursor() as cursor:
        cursor.execute("SELECT test_id FROM Questions WHERE id = ?", question_id)
        row = cursor.fetchone()
        if not row:
            return {'status': 'error', 'message': 'Вопрос не найден'}

        test_id = row.test_id
        cursor.execute("DELETE FROM Answers WHERE question_id = ?", question_id)
        cursor.execute("DELETE FROM Questions WHERE id = ?", question_id)
        db.commit()
        return {'status': 'ok', 'message': 'Вопрос удалён', 'test_id': test_id}


def handle_delete_answer(data):
    answer_id = data.get('answer_id')
    if not answer_id:
        return {'status': 'error', 'message': 'answer_id is required'}

    with db.cursor() as cursor:
        cursor.execute("SELECT question_id FROM Answers WHERE id = ?", answer_id)
        row = cursor.fetchone()
        if not row:
            return {'status': 'error', 'message': 'Ответ не найден'}

        cursor.execute("DELETE FROM Answers WHERE id = ?", answer_id)
        db.commit()
        return {'status': 'ok', 'message': 'Ответ удалён', 'question_id': row.question_id}


def handle_get_answer(data):
    answer_id = data.get('answer_id')
    if not answer_id:
        return {'status': 'error', 'message': 'answer_id is required'}

    with db.cursor() as cursor:
        cursor.execute("SELECT question_id, answer_text, is_correct FROM Answers WHERE id = ?", answer_id)
        row = cursor.fetchone()
        if not row:
            return {'status': 'error', 'message': 'Ответ не найден'}

        return {
            'status': 'ok',
            'answer_id': answer_id,
            'question_id': row.question_id,
            'text': row.answer_text,
            'is_correct': bool(row.is_correct)
        }


def handle_edit_answer(data):
    answer_id = data.get('answer_id')
    new_text = data.get('text')
    if not answer_id or new_text is None:
        return {'status': 'error', 'message': 'Недостаточно данных для обновления ответа'}

    with db.cursor() as cursor:
        cursor.execute("UPDATE Answers SET answer_text = ? WHERE id = ?", new_text, answer_id)
        db.commit()
        return {'status': 'ok', 'message': 'Ответ обновлён'}
def handle_delete_test(data):
    test_id = data.get('test_id')
    if not test_id:
        return {'status': 'error', 'message': 'test_id is required'}

    with db.cursor() as cursor:
        cursor.execute("DELETE FROM Answers WHERE question_id IN (SELECT id FROM Questions WHERE test_id = ?)", test_id)
        cursor.execute("DELETE FROM Questions WHERE test_id = ?", test_id)
        cursor.execute("DELETE FROM Tests WHERE id = ?", test_id)
        db.commit()

        return {'status': 'ok', 'message': 'Тест удалён'}

def handle_admin_get_logs():
    cursor = db.cursor()
    cursor.execute("SELECT TOP 100 * FROM Logs ORDER BY log_date DESC")
    rows = cursor.fetchall()
    logs = []
    for row in rows:
        logs.append({
            'id': row.id,
            'table': row.table_name,
            'action': row.action_type,
            'date': str(row.log_date),
            'user': row.user_id
        })
    return {'status': 'ok', 'logs': logs}

handlers = {
    'register': register_user,
    'login': login_user,
    'get_tests': lambda _: get_tests(),
    'get_questions': lambda data: get_test_questions(data['test_id']),
    'get_answers': handle_get_answers,
    'submit': submit_answers,
    'admin_add_test': handle_admin_add_test,
    'admin_add_question': handle_admin_add_question,
    'admin_add_answer': handle_admin_add_answer,
    'admin_stats': lambda _: handle_admin_statistics(),
    'delete_question': handle_delete_question,
    'delete_answer': handle_delete_answer,
    'get_answer': handle_get_answer,
    'admin_edit_answer': handle_edit_answer,
    'admin_get_logs': lambda _: handle_admin_get_logs(),
    'delete_test': handle_delete_test

}

def handle_client(conn):
    with conn:
        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    break
                request = jsonpickle.decode(data.decode())
                command = request.get('command')
                payload = request.get('data', {})
                print(f'[IN] {command}')
                handler = handlers.get(command)
                response = handler(payload) if handler else {'status': 'error', 'message': 'Unknown command'}
                conn.sendall(jsonpickle.encode(response).encode())
            except Exception as e:
                conn.sendall(jsonpickle.encode({'status': 'error', 'message': str(e)}).encode())
                break

def start_server():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            print(f'[SERVER] Запущен на {HOST}:{PORT}')
            while True:
                conn, addr = s.accept()
                print(f'[CONNECT] Клиент: {addr}')
                handle_client(conn)
    finally:
        db.close()
        print('[SERVER] Соединение с БД закрыто')

if __name__ == '__main__':
    start_server()
