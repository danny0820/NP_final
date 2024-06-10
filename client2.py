import pygame
import socket
import threading
import json

# 伺服器 IP 和埠
SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345

# 定義常量
SCREEN_WIDTH = 750
SCREEN_HEIGHT = 500
TANK_SIZE = 50
BULLET_SIZE = 5
BULLET_SPEED = 10
OBSTACLE_SIZE = 20  # 障礙物縮小後的尺寸
BG_COLOR = pygame.Color(0, 0, 0)
TEXT_COLOR = pygame.Color(255, 0, 0)

# 全局變量
tank_id = None
tank_position = None
tank_direction = 'U'  # 新增變量來記錄坦克方向
other_tank_position = None
other_tank_direction = 'U'  # 其他坦克的方向
bullets = []
explodes = []
sock = None
game_over = False
winner = None

# 加載坦克圖片
tank_images_yellow = {
    'U': pygame.image.load('./images/myTank/tank_T1_U.png'),
    'D': pygame.image.load('./images/myTank/tank_T1_D.png'),
    'L': pygame.image.load('./images/myTank/tank_T1_L.png'),
    'R': pygame.image.load('./images/myTank/tank_T1_R.png')
}

tank_images_green = {
    'U': pygame.image.load('./images/myTank/tank_T2_U.png'),
    'D': pygame.image.load('./images/myTank/tank_T2_D.png'),
    'L': pygame.image.load('./images/myTank/tank_T2_L.png'),
    'R': pygame.image.load('./images/myTank/tank_T2_R.png')
}

# 加載爆炸圖片
explode_images = [
    pygame.image.load('./images/myTank/boom_1.png'),
    pygame.image.load('./images/myTank/boom_2.png'),
    pygame.image.load('./images/myTank/boom_3.png'),
    pygame.image.load('./images/myTank/boom_4.png'),
    pygame.image.load('./images/myTank/boom_1.png'),
]

# 加載並縮小障礙物圖片
wood_box_image = pygame.image.load('./images/scene/brick.png')
wood_box_image = pygame.transform.scale(wood_box_image, (OBSTACLE_SIZE, OBSTACLE_SIZE))

iron_wall_image = pygame.image.load('./images/scene/iron.png')
iron_wall_image = pygame.transform.scale(iron_wall_image, (OBSTACLE_SIZE, OBSTACLE_SIZE))

# 爆炸效果類
class Explode:
    def __init__(self, position):
        self.images = explode_images
        self.position = position
        self.step = 0
        self.live = True

    def display_explode(self, window):
        if self.step < len(self.images):
            image = self.images[self.step]
            window.blit(image, self.position)
            self.step += 1
        else:
            self.live = False

# 障礙物類
class Obstacle:
    def __init__(self, position, obstacle_type):
        self.position = position
        self.type = obstacle_type
        self.image = wood_box_image if obstacle_type == 'wood' else iron_wall_image
        self.destroyable = obstacle_type == 'wood'
        self.live = True

    def display_obstacle(self, window):
        if self.live:
            window.blit(self.image, self.position)

# 處理來自伺服器的訊息
def handle_server_messages():
    global tank_id, tank_position, other_tank_position, bullets, other_tank_direction
    while True:
        try:
            data = sock.recv(1024).decode('utf-8')
            if not data:
                break
            message = json.loads(data)
            if message['type'] == 'init':
                tank_id = message['tank_id']
                tank_position = message['position']
                if tank_id == 1:
                    other_tank_position = [600, 400]
                else:
                    other_tank_position = [50, 50]
            elif message['type'] == 'move':
                if message['tank_id'] != tank_id:
                    other_tank_position = message['position']
                    other_tank_direction = message.get('direction', 'U')
            elif message['type'] == 'shoot':
                bullets.append(message['bullet'])
            elif message['type'] == 'full':
                print("Server is full")
                break
        except Exception as e:
            print(f"Error: {e}")
            break

# 初始化 pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('坦克大戰 - PVP')

# 從 JSON 檔案讀取地圖數據並初始化障礙物
def load_obstacles(filename):
    with open(filename, 'r') as f:
        map_data = json.load(f)
    obstacles = []
    map_height = len(map_data)
    map_width = len(map_data[0])
    start_x = (SCREEN_WIDTH - map_width * OBSTACLE_SIZE) // 2
    start_y = (SCREEN_HEIGHT - map_height * OBSTACLE_SIZE) // 2
    for y, row in enumerate(map_data):
        for x, cell in enumerate(row):
            position = [start_x + x * OBSTACLE_SIZE, start_y + y * OBSTACLE_SIZE]
            if cell == 1:
                obstacles.append(Obstacle(position, 'wood'))
            elif cell == 2:
                obstacles.append(Obstacle(position, 'iron'))
    return obstacles

# 初始障礙物
obstacles = load_obstacles('map_data.json')

# 持續移動
def move_tank(keys, tank_position):
    global tank_direction
    old_position = tank_position.copy()
    if keys[pygame.K_LEFT] and tank_position[0] > 0:
        tank_position[0] -= 5
        tank_direction = 'L'
    if keys[pygame.K_RIGHT] and tank_position[0] < SCREEN_WIDTH - TANK_SIZE:
        tank_position[0] += 5
        tank_direction = 'R'
    if keys[pygame.K_UP] and tank_position[1] > 0:
        tank_position[1] -= 5
        tank_direction = 'U'
    if keys[pygame.K_DOWN] and tank_position[1] < SCREEN_HEIGHT - TANK_SIZE:
        tank_position[1] += 5
        tank_direction = 'D'
    # 檢查與障礙物的碰撞
    if check_obstacle_collision(tank_position):
        tank_position[:] = old_position

# 發射子彈
def shoot_bullet(tank_position, direction):
    bullet_position = tank_position.copy()
    if direction == 'U':
        music = Music("./audios/fire.wav")
        music.playMusic()
        bullet_position[0] += TANK_SIZE // 2 - BULLET_SIZE // 2
        bullet_position[1] -= BULLET_SIZE
    elif direction == 'D':
        music = Music("./audios/fire.wav")
        music.playMusic()
        bullet_position[0] += TANK_SIZE // 2 - BULLET_SIZE // 2
        bullet_position[1] += TANK_SIZE
    elif direction == 'L':
        music = Music("./audios/fire.wav")
        music.playMusic()
        bullet_position[0] -= BULLET_SIZE
        bullet_position[1] += TANK_SIZE // 2 - BULLET_SIZE // 2
    elif direction == 'R':
        music = Music("./audios/fire.wav")
        music.playMusic()
        bullet_position[0] += TANK_SIZE
        bullet_position[1] += TANK_SIZE // 2 - BULLET_SIZE // 2
    bullet = {
        'tank_id': tank_id,
        'position': bullet_position,
        'direction': direction
    }
    bullets.append(bullet)
    message = {
        'type': 'shoot',
        'bullet': bullet
    }
    sock.sendall(json.dumps(message).encode('utf-8'))

# 更新子彈位置並檢查碰撞
def update_bullets():
    global bullets, game_over, winner, tank_position, other_tank_position
    new_bullets = []
    for bullet in bullets:
        if bullet['direction'] == 'U':
            bullet['position'][1] -= BULLET_SPEED
        elif bullet['direction'] == 'D':
            bullet['position'][1] += BULLET_SPEED
        elif bullet['direction'] == 'L':
            bullet['position'][0] -= BULLET_SPEED
        elif bullet['direction'] == 'R':
            bullet['position'][0] += BULLET_SPEED

        if 0 <= bullet['position'][0] <= SCREEN_WIDTH and 0 <= bullet['position'][1] <= SCREEN_HEIGHT:
            if bullet['tank_id'] != tank_id:
                if check_collision(bullet['position'], tank_position):
                    music = Music("./audios/bang.wav")
                    music.playMusic()
                    explodes.append(Explode(tank_position))
                    tank_position = None
                    game_over = True
                    winner = 'Player 2' if tank_id == 1 else 'Player 1'
            else:
                if check_collision(bullet['position'], other_tank_position):
                    music = Music("./audios/bang.wav")
                    music.playMusic()
                    explodes.append(Explode(other_tank_position))
                    other_tank_position = None
                    game_over = True
                    winner = 'Player 1' if tank_id == 1 else 'Player 2'
            # 檢查與障礙物的碰撞
            for obstacle in obstacles:
                if obstacle.live and check_collision(bullet['position'], obstacle.position):
                    if obstacle.destroyable:
                        obstacle.live = False
                    break
            else:
                new_bullets.append(bullet)
        else:
            continue
    bullets = new_bullets

# 檢查碰撞
def check_collision(bullet_position, tank_position):
    if tank_position:
        return bullet_position[0] in range(tank_position[0], tank_position[0] + TANK_SIZE) and \
               bullet_position[1] in range(tank_position[1], tank_position[1] + TANK_SIZE)
    return False

def check_obstacle_collision(tank_position):
    for obstacle in obstacles:
        if obstacle.live:
            if tank_position[0] + TANK_SIZE > obstacle.position[0] and tank_position[0] < obstacle.position[0] + OBSTACLE_SIZE and \
               tank_position[1] + TANK_SIZE > obstacle.position[1] and tank_position[1] < obstacle.position[1] + OBSTACLE_SIZE:
                return True
    return False

# 顯示遊戲結束畫面
def display_game_over(window, winner):
    text = f'{winner} wins!'
    game_over_surface = get_text_surface(text)
    window.blit(game_over_surface, (SCREEN_WIDTH // 2 - game_over_surface.get_width() // 2, SCREEN_HEIGHT // 2))

# 獲取文字表面
def get_text_surface(text):
    pygame.font.init()
    font = pygame.font.Font('./font/simkai.ttf', 18)
    text_surface = font.render(text, True, TEXT_COLOR)
    return text_surface

class Music():
    def __init__(self, filename) -> None:
        self.filename = filename
        pygame.mixer.init()
        pygame.mixer.music.load(self.filename)

    def playMusic(self):
        pygame.mixer.music.play()

class MainGame:
    window = None

    @staticmethod
    def main_loop():
        global tank_position, tank_direction, game_over, winner
        clock = pygame.time.Clock()

        while True:
            if game_over:
                MainGame.window.fill(BG_COLOR)
                display_game_over(MainGame.window, winner)
                for explode in explodes:
                    explode.display_explode(MainGame.window)
                pygame.display.update()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sock.close()
                        return

            else:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sock.close()
                        return
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE:
                            shoot_bullet(tank_position, tank_direction)

                keys = pygame.key.get_pressed()
                old_position = tank_position.copy() if tank_position else None
                move_tank(keys, tank_position)

                if old_position and old_position != tank_position:
                    message = {
                        'type': 'move',
                        'position': tank_position,
                        'direction': tank_direction
                    }
                    sock.sendall(json.dumps(message).encode('utf-8'))

                update_bullets()

                MainGame.window.fill(BG_COLOR)
                if tank_position:
                    MainGame.window.blit(tank_images_yellow[tank_direction], tank_position) if tank_id == 1 else MainGame.window.blit(tank_images_green[tank_direction], tank_position)
                if other_tank_position:
                    MainGame.window.blit(tank_images_green[other_tank_direction], other_tank_position) if tank_id == 1 else MainGame.window.blit(tank_images_yellow[other_tank_direction], other_tank_position)
                for bullet in bullets:
                    pygame.draw.rect(MainGame.window, (255, 255, 255), (*bullet['position'], BULLET_SIZE, BULLET_SIZE))
                for explode in explodes:
                    explode.display_explode(MainGame.window)
                for obstacle in obstacles:
                    obstacle.display_obstacle(MainGame.window)
                pygame.display.update()
                clock.tick(30)

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_IP, SERVER_PORT))
    threading.Thread(target=handle_server_messages).start()
    MainGame.window = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('坦克大戰 - PVP')
    MainGame.main_loop()
