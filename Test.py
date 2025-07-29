import os
import socket

user_name = os.getlogin()
computer_name = socket.gethostname()

print(f"User: {user_name}, Computer: {computer_name}")

import os

system_user = os.getlogin()

print(f"System User: {system_user}")
