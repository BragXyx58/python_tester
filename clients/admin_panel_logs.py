import socket
import jsonpickle
import tkinter as tk
from tkinter import ttk, messagebox

HOST = '127.0.0.1'
PORT = 4000

def request_logs():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            request = {'command': 'admin_get_logs'}
            s.sendall(jsonpickle.encode(request).encode())
            response = jsonpickle.decode(s.recv(100000).decode())
            return response
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def refresh_logs():
    logs_tree.delete(*logs_tree.get_children())
    result = request_logs()

    if result['status'] == 'ok':
        for log in result['logs']:
            logs_tree.insert('', 'end', values=(
                log['id'], log['table'], log['action'], log['date'], log['user']
            ))
    else:
        messagebox.showerror("Ошибка", result['message'])

root = tk.Tk()
root.title("Админ-панель логов")
root.geometry("800x400")

columns = ('id', 'table', 'action', 'date', 'user')
logs_tree = ttk.Treeview(root, columns=columns, show='headings')
for col in columns:
    logs_tree.heading(col, text=col.capitalize())
    logs_tree.column(col, width=150 if col != 'id' else 50)

logs_tree.pack(expand=True, fill='both', padx=10, pady=10)

refresh_button = tk.Button(root, text="Обновить логи", command=refresh_logs)
refresh_button.pack(pady=5)

refresh_logs()
root.mainloop()
