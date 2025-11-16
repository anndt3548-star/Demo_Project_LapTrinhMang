import socketio
import time
import threading

SERVER = 'http://127.0.0.1:5001'


def make_client(name, choice):
    sio = socketio.Client()
    state = {'room': None}

    @sio.event
    def connect():
        print(f"[{name}] connected")
        sio.emit('join', {'name': name})

    @sio.on('start')
    def on_start(data):
        state['room'] = data.get('room')
        opp = data.get('opponent')
        print(f"[{name}] matched vs {opp}, room={state['room']}")

        # send choice in a background task so we don't block the event thread
        def send_choice():
            time.sleep(1.0)
            try:
                sio.emit('play', {'room': state['room'], 'choice': str(choice)})
                print(f"[{name}] sent choice {choice}")
            except Exception as e:
                print(f"[{name}] emit error: {e}")

        try:
            sio.start_background_task(send_choice)
        except Exception:
            # fallback
            t = threading.Thread(target=send_choice, daemon=True)
            t.start()

    @sio.on('countdown')
    def on_countdown(d):
        print(f"[{name}] countdown: {d.get('seconds')}")

    @sio.on('result')
    def on_result(d):
        print(f"[{name}] RESULT: {d.get('msg')}")

    @sio.on('message')
    def on_message(d):
        print(f"[{name}] MSG: {d.get('msg')}")

    @sio.on('score')
    def on_score(d):
        print(f"[{name}] SCORE: {d}")

    def run():
        try:
            sio.connect(SERVER)
            # keep client alive while the game runs
            time.sleep(15)
        except Exception as e:
            print(f"[{name}] connection error: {e}")
        finally:
            try:
                sio.disconnect()
            except:
                pass

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


if __name__ == '__main__':
    print('Starting two simulated web clients (Alice -> choice 1, Bob -> choice 2)')
    t1 = make_client('Alice', 1)
    time.sleep(0.3)
    t2 = make_client('Bob', 2)

    # wait for both threads to finish (or timeout)
    start = time.time()
    while time.time() - start < 20:
        time.sleep(0.5)
    print('Done')
