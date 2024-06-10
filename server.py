import socket
import threading
import json

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345

# 記錄連接的玩家
players = {}
bullets = []
player_count = 0
lock = threading.Lock()

# 廣播訊息給所有玩家
def broadcast(message, exclude_sock=None):
    with lock:
        for sock in players:
            if sock != exclude_sock:
                sock.sendall(json.dumps(message).encode('utf-8'))

# 處理玩家連線
def handle_client(sock, addr):
    global player_count
    with lock:
        player_count += 1
        player_id = player_count
        players[sock] = {
            'tank_id': player_id,
            'position': [50, 50] if player_id == 1 else [600, 400],
            'direction': 'U'
        }

    try:
        init_message = {
            'type': 'init',
            'tank_id': players[sock]['tank_id'],
            'position': players[sock]['position']
        }
        sock.sendall(json.dumps(init_message).encode('utf-8'))

        while True:
            data = sock.recv(1024).decode('utf-8')
            if not data:
                break
            message = json.loads(data)
            print(f"Received message from Player {players[sock]['tank_id']}: {message}")
            if message['type'] == 'move':
                with lock:
                    players[sock]['position'] = message['position']
                    players[sock]['direction'] = message['direction']
                broadcast({
                    'type': 'move',
                    'tank_id': players[sock]['tank_id'],
                    'position': message['position'],
                    'direction': message['direction']
                }, exclude_sock=sock)
            elif message['type'] == 'shoot':
                with lock:
                    bullets.append(message['bullet'])
                broadcast({
                    'type': 'shoot',
                    'bullet': message['bullet']
                }, exclude_sock=sock)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        with lock:
            print(f"Player {players[sock]['tank_id']} disconnected")
            del players[sock]
        sock.close()

# 啟動伺服器
def start_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((SERVER_IP, SERVER_PORT))
    server_sock.listen(5)
    print(f"Server started at {SERVER_IP}:{SERVER_PORT}")

    while True:
        client_sock, client_addr = server_sock.accept()
        with lock:
            if len(players) < 2:
                print(f"Player connected from {client_addr}")
                threading.Thread(target=handle_client, args=(client_sock, client_addr)).start()
            else:
                client_sock.sendall(json.dumps({'type': 'full'}).encode('utf-8'))
                client_sock.close()

if __name__ == '__main__':
    start_server()
