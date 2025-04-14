import socket
import jsonpickle
import hashlib
import tkinter as tk
from tkinter import messagebox

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

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("HTTP Test System")
        self.user = None
        self.test_data = []
        self.current_q = 0
        self.answers = []
        self.selected_var = tk.IntVar()
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
            if res['status'] == 'ok':
                self.user = {'id': res['user_id'], 'username': username.get()}
                self.show_test_list()
            else:
                messagebox.showerror("Ошибка", res['message'])

        def register():
            res = send('register', {
                'username': username.get(),
                'password': password.get()
            })
            messagebox.showinfo("Регистрация", res['message'])

        tk.Button(self.root, text="Войти", command=login).pack(pady=5)
        tk.Button(self.root, text="Регистрация", command=register).pack()

    def show_test_list(self):
        self.clear()
        tests = send('get_tests', {})
        tk.Label(self.root, text="Выберите тест").pack()
        for test in tests:
            tk.Button(self.root, text=f"{test['title']}: {test['description']}",
                      command=lambda tid=test['id']: self.start_test(tid)).pack(pady=2)

        tk.Button(self.root, text="Выход", command=self.show_login).pack(pady=10)

    def start_test(self, test_id):
        self.test_data = send('get_questions', {'test_id': test_id})[
            'questions']
        print(self.test_data)
        self.test_id = test_id
        self.answers = []
        self.current_q = 0
        self.show_question()

    def show_question(self):
        self.clear()
        if self.current_q >= len(self.test_data):
            return self.finish_test()

        q = self.test_data[self.current_q]
        tk.Label(self.root, text=q['text'], font=("Arial", 14)).pack(pady=10)

        self.selected_var.set(-1)
        for ans in q['answers']:
            tk.Radiobutton(self.root, text=ans['text'], variable=self.selected_var, value=ans['id']).pack(anchor="w")

        def next_q():
            sel = self.selected_var.get()
            if sel == -1:
                messagebox.showwarning("Ошибка", "Выберите ответ")
                return
            self.answers.append({'question_id': q['id'], 'answer_id': sel})
            self.current_q += 1
            self.show_question()

        tk.Button(self.root, text="Далее", command=next_q).pack(pady=10)

    def finish_test(self):
        result = send('submit', {
            'user_id': self.user['id'],
            'test_id': self.test_id,
            'answers': self.answers
        })
        self.clear()
        tk.Label(self.root, text="Результат теста", font=("Arial", 14)).pack(pady=10)
        tk.Label(self.root, text=f"Правильных ответов: {result['correct']} из {result['total']}").pack()
        tk.Label(self.root, text=f"Процент: {result['percent']}%").pack(pady=10)
        tk.Button(self.root, text="Назад к тестам", command=self.show_test_list).pack()

if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("600x600")
    app = App(root)
    root.mainloop()
