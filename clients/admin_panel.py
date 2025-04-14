import tkinter as tk
from tkinter import messagebox, ttk
import hashlib
import jsonpickle
import socket

HOST = '127.0.0.1'
PORT = 4000


def send(command, data):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        request = jsonpickle.encode({'command': command, 'data': data})
        s.sendall(request.encode())
        response = s.recv(8192)
        return jsonpickle.decode(response.decode())


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


class AdminPanelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Административная панель")
        self.user = None
        self.show_login()

    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear()
        tk.Label(self.root, text="Имя пользователя").pack()
        username = tk.Entry(self.root)
        username.pack()
        tk.Label(self.root, text="Пароль").pack()
        password = tk.Entry(self.root, show="*")
        password.pack()

        def login():
            res = send('login', {
                'username': username.get(),
                'password': password.get()
            })
            if res['status'] == 'ok' and res.get('is_admin'):
                self.user = {'id': res['user_id'], 'username': username.get()}
                self.show_admin_dashboard()
            else:
                messagebox.showerror("Ошибка", "Неверный логин или пароль, либо у вас нет прав администратора.")

        tk.Button(self.root, text="Войти", command=login).pack(pady=5)

    def show_admin_dashboard(self):
        self.clear()
        tk.Label(self.root, text="Добро пожаловать, Администратор!", font=("Arial", 14)).pack(pady=10)

        # Добавить тест
        tk.Button(self.root, text="Добавить новый тест", command=self.add_test).pack(pady=5)
        # Просмотр статистики
        tk.Button(self.root, text="Просмотр статистики", command=self.view_statistics).pack(pady=5)
        # Управление тестами
        tk.Button(self.root, text="Управление тестами", command=self.manage_tests).pack(pady=5)
        # Выход
        tk.Button(self.root, text="Выход", command=self.show_login).pack(pady=10)

    def add_test(self):
        self.clear()
        tk.Label(self.root, text="Название теста").pack()
        test_title = tk.Entry(self.root)
        test_title.pack()
        tk.Label(self.root, text="Описание теста").pack()
        test_description = tk.Entry(self.root)
        test_description.pack()

        def save_test():
            test_data = {
                'title': test_title.get(),
                'description': test_description.get()
            }
            res = send('admin_add_test', test_data)
            messagebox.showinfo("Добавление теста", res['message'])
            self.show_admin_dashboard()

        tk.Button(self.root, text="Сохранить тест", command=save_test).pack(pady=5)
        tk.Button(self.root, text="Назад", command=self.show_admin_dashboard).pack(pady=10)

    def view_statistics(self):
        self.clear()
        stats = send('admin_stats', {})

        if not stats:
            messagebox.showinfo("Статистика", "Нет данных для отображения.")
            self.show_admin_dashboard()
            return

        tree = ttk.Treeview(self.root, columns=("user", "test", "date", "score"), show="headings")
        tree.heading("user", text="Пользователь")
        tree.heading("test", text="Тест")
        tree.heading("date", text="Дата")
        tree.heading("score", text="Процент")

        for stat in stats:
            tree.insert("", "end", values=(stat['user'], stat['test'], stat['date'], f"{stat['score']}%"))

        tree.pack(pady=10)
        tk.Button(self.root, text="Назад", command=self.show_admin_dashboard).pack(pady=10)

    def manage_tests(self):
        self.clear()
        tests = send('get_tests', {})

        if not tests:
            messagebox.showinfo("Управление тестами", "Нет тестов для управления.")
            self.show_admin_dashboard()
            return

        tk.Label(self.root, text="Выберите тест для управления:").pack(pady=10)

        for test in tests:
            tk.Button(self.root, text=f"{test['title']}", command=lambda tid=test['id']: self.manage_test(tid)).pack(
                pady=2)

            def delete_test(test_id=test['id']):
                res = send('delete_test', {'test_id': test_id})
                messagebox.showinfo("Удаление теста", res['message'])
                self.manage_tests()

            tk.Button(self.root, text="Удалить тест", command=delete_test).pack(pady=5)

        tk.Button(self.root, text="Назад", command=self.show_admin_dashboard).pack(pady=10)

    def manage_test(self, test_id):
        self.clear()
        test_data = send('get_questions', {'test_id': test_id})

        tk.Label(self.root, text="Управление тестом", font=("Arial", 14)).pack(pady=10)

        # Добавление вопроса
        tk.Button(self.root, text="Добавить новый вопрос", command=lambda: self.add_question(test_id)).pack(pady=5)

        if 'questions' in test_data:
            for question in test_data['questions']:
                tk.Button(self.root, text=question['text'],
                          command=lambda qid=question['id']: self.manage_question(qid)).pack(pady=2)

        tk.Button(self.root, text="Назад", command=self.show_admin_dashboard).pack(pady=10)

    def add_question(self, test_id):
        self.clear()
        tk.Label(self.root, text="Текст вопроса").pack()
        question_text = tk.Entry(self.root)
        question_text.pack()

        def save_question():
            question_data = {
                'test_id': test_id,
                'text': question_text.get()
            }
            res = send('admin_add_question', question_data)
            messagebox.showinfo("Добавление вопроса", res['message'])
            self.manage_test(test_id)

        tk.Button(self.root, text="Сохранить вопрос", command=save_question).pack(pady=5)
        tk.Button(self.root, text="Назад", command=lambda: self.manage_test(test_id)).pack(pady=10)

    def manage_question(self, question_id):
        self.clear()
        question_data = send('get_answers', {'question_id': question_id})

        if not question_data or 'answers' not in question_data:
            messagebox.showinfo("Ошибка", "Нет ответов для этого вопроса.")
            return

        answers = question_data['answers']
        tk.Label(self.root, text="Управление вопросом", font=("Arial", 14)).pack(pady=10)

        for answer in answers:
            tk.Button(self.root, text=answer['text'],
                      command=lambda aid=answer['id']: self.manage_answer(aid)).pack(pady=2)

        def delete_question():
            res = send('delete_question', {'question_id': question_id})
            messagebox.showinfo("Удаление вопроса", res['message'])
            self.manage_test(res.get('test_id'))

        tk.Button(self.root, text="Добавить новый ответ", command=lambda: self.add_answer(question_id)).pack(pady=5)
        tk.Button(self.root, text="Удалить вопрос", command=delete_question).pack(pady=5)
        tk.Button(self.root, text="Назад", command=lambda: self.manage_test(question_data.get('test_id'))).pack(pady=10)

    def add_answer(self, question_id):
        self.clear()
        tk.Label(self.root, text="Текст ответа").pack()
        answer_text = tk.Entry(self.root)
        answer_text.pack()

        is_correct_var = tk.BooleanVar()
        tk.Checkbutton(self.root, text="Это правильный ответ", variable=is_correct_var).pack()

        def save_answer():
            res = send('admin_add_answer', {
                'question_id': question_id,
                'text': answer_text.get(),
                'is_correct': is_correct_var.get()
            })
            messagebox.showinfo("Добавление ответа", res['message'])
            self.manage_question(question_id)

        tk.Button(self.root, text="Сохранить ответ", command=save_answer).pack(pady=5)
        tk.Button(self.root, text="Назад", command=lambda: self.manage_question(question_id)).pack(pady=10)

    def manage_answer(self, answer_id):
        self.clear()
        answer_data = send('get_answer', {'answer_id': answer_id})

        tk.Label(self.root, text="Управление ответом", font=("Arial", 14)).pack(pady=10)

        # Редактирование текста ответа
        tk.Label(self.root, text="Новый текст ответа").pack()
        new_answer_text = tk.Entry(self.root)
        new_answer_text.insert(0, answer_data['text'])
        new_answer_text.pack()

        def save_answer():
            res = send('admin_edit_answer', {
                'answer_id': answer_id,
                'text': new_answer_text.get()
            })
            messagebox.showinfo("Редактирование ответа", res['message'])
            self.manage_question(answer_data['question_id'])

        tk.Button(self.root, text="Сохранить ответ", command=save_answer).pack(pady=5)

        # Удалить ответ
        def delete_answer():
            res = send('delete_answer', {'answer_id': answer_id})
            messagebox.showinfo("Удаление ответа", res['message'])
            self.manage_question(answer_data['question_id'])

        tk.Button(self.root, text="Удалить ответ", command=delete_answer).pack(pady=5)
        tk.Button(self.root, text="Назад", command=lambda: self.manage_question(answer_data['question_id'])).pack(
            pady=10)


if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("600x600")
    app = AdminPanelApp(root)
    root.mainloop()
