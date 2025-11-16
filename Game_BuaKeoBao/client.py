
import socket
import threading

HOST = '127.0.0.1'
PORT = 5555

def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if message:
                print(message, end='')
            else:
                break
        except:
            print("Mất kết nối với server!")
            break
    client_socket.close()

def start_client():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((HOST, PORT))
    except:
        print("Không thể kết nối đến server!")
        return

    # Luồng nhận tin nhắn từ server
    receive_thread = threading.Thread(target=receive_messages, args=(client,))
    receive_thread.start()

    # Gửi dữ liệu từ người dùng
    while True:
        try:
            message = input("")
            if message.lower() == 'q':
                client.send('q'.encode('utf-8'))
                break
            client.send(message.encode('utf-8'))
        except:
            break

    client.close()

if __name__ == "__main__":
    print("=== Game Búa Kéo Bao Online ===")
    start_client()