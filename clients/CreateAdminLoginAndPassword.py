import hashlib
username = 'admin'
password = 'admin'
hashed_password = hashlib.sha256(password.encode()).hexdigest()
print(f"Зашифрованный пароль для пользователя '{username}': {hashed_password}")