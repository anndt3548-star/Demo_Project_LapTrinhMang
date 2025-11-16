import socket
import threading
import queue

HOST = '127.0.0.1'
PORT = 5555

waiting_queue = queue.Queue()
games = {}
game_done_events = {}
lock = threading.Lock()

choices = {'1': 'Đá', '2': 'Kéo', '3': 'Bao'}


def play_game(p1_socket, p2_socket, p1_name, p2_name, game_event):
    """Chạy trò chơi giữa hai client."""
    def send_to_both(msg):
        try:
            p1_socket.send(msg.encode('utf-8'))
        except:
            pass
        try:
            p2_socket.send(msg.encode('utf-8'))
        except:
            pass

    try:
        while True:
            try:
                # Gửi prompt
                send_to_both("\n=== Lượt mới ===\nChọn: 1.Đá  2.Kéo  3.Bao  (hoặc 'q' để thoát): ")

                # Nhận lựa chọn
                p1_socket.settimeout(30)
                p2_socket.settimeout(30)
                p1_choice = p1_socket.recv(1024).decode('utf-8').strip().lower()
                p2_choice = p2_socket.recv(1024).decode('utf-8').strip().lower()

                if p1_choice == 'q' or p2_choice == 'q':
                    send_to_both("Trò chơi kết thúc.\n")
                    break

                if p1_choice not in ['1', '2', '3'] or p2_choice not in ['1', '2', '3']:
                    send_to_both("Lựa chọn không hợp lệ! Vui lòng chọn lại.\n")
                    continue

                p1_move = choices[p1_choice]
                p2_move = choices[p2_choice]

                # Tính toán kết quả
                result_msg = f"\n{p1_name} ra: {p1_move} | {p2_name} ra: {p2_move}\n"

                if p1_choice == p2_choice:
                    result = "Hòa!"
                elif (p1_choice == '1' and p2_choice == '2') or \
                     (p1_choice == '2' and p2_choice == '3') or \
                     (p1_choice == '3' and p2_choice == '1'):
                    result = f"{p1_name} thắng!"
                else:
                    result = f"{p2_name} thắng!"

                final_msg = result_msg + result + "\n"
                send_to_both(final_msg)

            except socket.timeout:
                send_to_both("Hết thời gian chờ! Trò chơi kết thúc.\n")
                break
            except Exception:
                send_to_both("Đối thủ đã ngắt kết nối!\n")
                break

    finally:
        # Đóng socket và báo game kết thúc
        try:
            p1_socket.close()
        except:
            pass
        try:
            p2_socket.close()
        except:
            pass
        if game_event:
            game_event.set()


def handle_client(client_socket, addr):
    """Xử lý mỗi client kết nối."""
    game_event = None
    try:
        # Nhận tên với timeout
        client_socket.settimeout(30)
        client_socket.send("Nhập tên của bạn: ".encode('utf-8'))
        name = client_socket.recv(1024).decode('utf-8').strip()
        if not name:
            name = "Player"

        client_socket.send(f"Chào {name}! Đang chờ đối thủ...\n".encode('utf-8'))
        client_socket.settimeout(None)  # Reset timeout

        # Thêm vào queue hoặc ghép cặp
        with lock:
            if waiting_queue.empty():
                # Người chơi đầu tiên
                game_event = threading.Event()
                waiting_queue.put((client_socket, name, addr, game_event))
                client_socket.send("Bạn đã vào hàng đợi. Chờ người chơi khác...\n".encode('utf-8'))
            else:
                # Người chơi thứ hai - ghép cặp
                opp_socket, opp_name, opp_addr, opp_event = waiting_queue.get()
                game_event = opp_event  # Dùng event của client 1

                # Thông báo bắt đầu
                start_msg = f"Đã tìm thấy đối thủ: {opp_name}! Trận đấu bắt đầu!\n"
                client_socket.send(start_msg.encode('utf-8'))
                opp_socket.send(f"Đã tìm thấy đối thủ: {name}! Trận đấu bắt đầu!\n".encode('utf-8'))

                # Chạy game trong thread riêng, cả 2 handler đều chờ event
                game_thread = threading.Thread(
                    target=play_game,
                    args=(opp_socket, client_socket, opp_name, name, game_event)
                )
                game_thread.daemon = True
                game_thread.start()

        # Chờ game kết thúc (signal từ play_game)
        if game_event:
            game_event.wait()

    except socket.timeout:
        print(f"Timeout với client {addr}")
    except Exception as e:
        print(f"Lỗi với client {addr}: {e}")
    finally:
        try:
            client_socket.close()
        except:
            pass


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[SERVER] Đang chạy trên {HOST}:{PORT}")

    try:
        while True:
            client_socket, addr = server.accept()
            print(f"[KẾT NỐI] {addr} đã kết nối.")
            thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            thread.daemon = True
            thread.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Đóng server.")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()