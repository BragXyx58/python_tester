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

def register_user(data):
    with db.cursor() as cursor:
        cursor.execute("SELECT id FROM Users WHERE username = ?", data['username'])
        if cursor.fetchone():
            return {'status': 'error', 'message': 'Пользователь уже существует'}
        cursor.execute("INSERT INTO Users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                       data['username'], hash_password(data['password']), data.get('is_admin', 0))
        db.commit()
        return {'status': 'ok', 'message': 'Регистрация успешна'}

def login_user(data):
    with db.cursor() as cursor:
        cursor.execute("SELECT id, is_admin FROM Users WHERE username = ? AND password_hash = ?",
                       data['username'], hash_password(data['password']))
        user = cursor.fetchone()
        if user:
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
        print(questions)
        return questions

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

handlers = {
    'register': register_user,
    'login': login_user,
    'get_tests': lambda _: get_tests(),
    'get_questions': lambda data: get_test_questions(data['test_id']),
    'submit': submit_answers,
    'admin_add_test': handle_admin_add_test,
    'admin_add_question': handle_admin_add_question,
    'admin_add_answer': handle_admin_add_answer,
    'admin_stats': lambda _: handle_admin_statistics(),
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
