from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import time
import os

app = Flask(__name__, static_folder='images', static_url_path='/images')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# Simple matchmaking queue
waiting = []  # list of (sid, name, event)
games = {}    # room_id -> { 'p1': sid, 'p2': sid, 'names': {sid: name}, 'choices': {}, 'score': {}, 'history': [] }


@app.route('/')
def index():
    return render_template('index.html')


def game_loop(room):
    """Background loop for rounds: emit countdowns, collect choices, compute results, update score/history."""
    g = games.get(room)
    if not g:
        return
    p1 = g['p1']
    p2 = g['p2']
    name1 = g['names'].get(p1)
    name2 = g['names'].get(p2)

    while room in games:
        # start round with countdown
        countdown = 8
        for s in range(countdown, 0, -1):
            socketio.emit('countdown', {'seconds': s}, room=room)
            time.sleep(1)

        # evaluate choices collected during countdown
        c1 = g['choices'].get(p1)
        c2 = g['choices'].get(p2)
        mapping = {'1': 'Đá', '2': 'Kéo', '3': 'Bao'}
        move1 = mapping.get(c1, '---')
        move2 = mapping.get(c2, '---')

        if not c1 and not c2:
            result = 'Không có người chơi nào chọn. Hòa.'
        elif not c1:
            result = f"{name2} thắng (đối thủ không chọn)!"
            g['score'][p2] += 1
        elif not c2:
            result = f"{name1} thắng (đối thủ không chọn)!"
            g['score'][p1] += 1
        else:
            if c1 == c2:
                result = 'Hòa!'
            elif (c1 == '1' and c2 == '2') or (c1 == '2' and c2 == '3') or (c1 == '3' and c2 == '1'):
                result = f"{name1} thắng!"
                g['score'][p1] += 1
            else:
                result = f"{name2} thắng!"
                g['score'][p2] += 1

        final_msg = f"{name1} ra: {move1} | {name2} ra: {move2} - {result}"
        g['history'].append(final_msg)

        socketio.emit('result', {'msg': final_msg}, room=room)
        # emit score and history
        score_payload = {g['names'][p1]: g['score'][p1], g['names'][p2]: g['score'][p2]}
        socketio.emit('score', {'score': score_payload}, room=room)
        socketio.emit('history', {'history': g['history']}, room=room)

        # prepare next round
        g['choices'] = {}
        time.sleep(1)


@socketio.on('join')
def on_join(data):
    name = data.get('name') or 'Player'
    sid = request.sid
    # Store name in waiting list entry
    waiting.append((sid, name))
    emit('message', {'msg': 'Bạn đã vào hàng đợi. Chờ đối thủ...'}, to=sid)

    # If there is another player waiting, create a room
    if len(waiting) >= 2:
        (sid1, name1) = waiting.pop(0)
        (sid2, name2) = waiting.pop(0)
        room = str(uuid.uuid4())
        games[room] = {'p1': sid1, 'p2': sid2, 'names': {sid1: name1, sid2: name2}, 'choices': {}, 'score': {sid1:0, sid2:0}, 'history': []}
        join_room(room, sid=sid1)
        join_room(room, sid=sid2)
        socketio.emit('start', {'room': room, 'opponent': name2}, to=sid1)
        socketio.emit('start', {'room': room, 'opponent': name1}, to=sid2)

        # start game loop in background
        socketio.start_background_task(game_loop, room)


@socketio.on('play')
def on_play(data):
    room = data.get('room')
    choice = data.get('choice')
    sid = request.sid
    if room not in games:
        emit('message', {'msg': 'Trận đấu không tồn tại.'}, to=sid)
        return
    g = games[room]
    # only accept choices from players in the game
    if sid != g['p1'] and sid != g['p2']:
        emit('message', {'msg': 'Bạn không thuộc trận đấu này.'}, to=sid)
        return
    g['choices'][sid] = choice
    emit('message', {'msg': f'Bạn chọn: {choice}'}, to=sid)


@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    # remove from waiting
    for i, (wsid, name) in enumerate(list(waiting)):
        if wsid == sid:
            waiting.pop(i)
            break
    # find any game containing sid and notify opponent
    for room, g in list(games.items()):
        if sid == g.get('p1') or sid == g.get('p2'):
            opp = g['p2'] if sid == g.get('p1') else g['p1']
            try:
                socketio.emit('message', {'msg': 'Đối thủ đã thoát. Trận đấu kết thúc.'}, to=opp)
            except:
                pass
            # clean up
            try:
                del games[room]
            except:
                pass


if __name__ == '__main__':
    # Use port 5001 to avoid conflicts
    socketio.run(app, host='0.0.0.0', port=5001)


# Flask will serve files from the `images/` folder at the `/images/...` URL
