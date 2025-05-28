import pygame
import sys
import time
import random
from pygame.locals import *

# Constants
GRID_SIZE = 25
CELL_SIZE = 20
PANEL_WIDTH = 150
WINDOW_WIDTH = GRID_SIZE * CELL_SIZE + 2 * PANEL_WIDTH
WINDOW_HEIGHT = GRID_SIZE * CELL_SIZE
TIME_LIMIT = 90  # seconds
FOOD_SPAWN_INTERVAL = 5000  # milliseconds
AI_SPAWN_TIMES = [30000, 60000]  # 적 뱀 등장 시간 (ms)

# 먹이 등장 시간과 먹이 점수 
FOOD_UNLOCK_TIMES = [0, 18000, 36000, 54000, 72000]
FOOD_SCORES = [100, 150, 200, 250, 300]

# 커스텀 이벤트
SPAWN_FOOD_EVENT = USEREVENT + 1
SPAWN_AI_EVENT_30 = USEREVENT + 2
SPAWN_AI_EVENT_60 = USEREVENT + 3
# 색 
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (50, 50, 50)

# 방향 
dirs = {
    'UP': (0, -1),
    'DOWN': (0, 1),
    'LEFT': (-1, 0),
    'RIGHT': (1, 0),
}

class Snake:
    def __init__(self, start_pos, color, is_player=False):
        self.body = [start_pos[:]]
        self.direction = 'RIGHT'
        self.pending_direction = 'RIGHT'
        self.color = color
        self.is_player = is_player
        self.alive = True
        self.base_speed = 200
        self.speed = self.base_speed
        self.last_move_time = pygame.time.get_ticks()
        self.spawn_pos = start_pos[:]
        
        # 시작 길이 = 5 
        for _ in range(4):
            self.grow()

    def set_direction(self, new_dir):
        opposites = {
            'UP': 'DOWN',
            'DOWN': 'UP',
            'LEFT': 'RIGHT',
            'RIGHT': 'LEFT',
        }
        if new_dir != opposites[self.direction]:
            self.pending_direction = new_dir

    def update(self, now):
        if not self.alive:
            return
        if now - self.last_move_time >= self.speed:
            self.direction = self.pending_direction
            dx, dy = dirs[self.direction]
            head_x, head_y = self.body[0]
            new_head = [head_x + dx, head_y + dy]
            self.body.insert(0, new_head)
            self.body.pop()
            self.last_move_time = now

    def grow(self):
        tail = self.body[-1][:]
        self.body.append(tail)

    def head_pos(self):
        return tuple(self.body[0])

    def length(self):
        return len(self.body)

    def die(self):
        self.alive = False
        self.death_time = pygame.time.get_ticks()

    def revive(self):
        self.body = [self.spawn_pos[:]]
        self.direction = 'RIGHT'
        self.pending_direction = 'RIGHT'
        self.alive = True
        self.speed = self.base_speed
        self.last_move_time = pygame.time.get_ticks()
        for _ in range(4):
            self.grow()

    def draw(self, surface, offset_x):
        for segment in self.body:
            x, y = segment
            pygame.draw.rect(
                surface, self.color,
                (offset_x + x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            )

class AiSnake(Snake):
    def __init__(self, start_pos, color):
        super().__init__(start_pos, color, is_player=False)


    def update(self, now):
        if not self.alive:
            # 3초 후 부활 
            if now - self.death_time >= 3000:
                self.revive()
            return
        # 랜덤 방향 변경
        safe_dirs = []

        if random.random() < 0.1:
            x, y = self.body[0]
            for d, (dx, dy) in dirs.items():
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    safe_dirs.append(d)
        if safe_dirs:
            self.pending_direction = random.choice(safe_dirs)

                
        # 벽 이동 방지
        x, y = self.body[0]
        dx, dy = dirs[self.pending_direction]
        if not (0 <= x + dx < GRID_SIZE and 0 <= y + dy < GRID_SIZE):
            safe_dirs = []
            for d, (dx, dy) in dirs.items():
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    safe_dirs.append(d)
            if safe_dirs:
                self.pending_direction = random.choice(safe_dirs)
                
        super().update(now)

class Food:
    def __init__(self, pos, score):
        self.pos = pos
        self.score = score

    def draw(self, surface, offset_x):
        margin = CELL_SIZE // 4
        x, y = self.pos
        pygame.draw.rect(
            surface, BLUE,
            (offset_x + x * CELL_SIZE + margin,
             y * CELL_SIZE + margin,
             CELL_SIZE - 2 * margin,
             CELL_SIZE - 2 * margin)
        )

class Game:
    SCORE_FILE = 'highscore.txt'

    def __init__(self):
        pygame.init()
        self.window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Snake Eater Advanced')
        self.font = pygame.font.SysFont('consolas', 20)
        self.start_time = pygame.time.get_ticks()
        self.high_score = 0
        # 점수 불러오기 
        try:
            with open(self.SCORE_FILE, 'r') as f:
                self.high_score = int(f.read())
        except:
            self.high_score = 0


        self.left_offset = 0
        self.game_offset = PANEL_WIDTH
        self.right_offset = PANEL_WIDTH + GRID_SIZE * CELL_SIZE

        # 플레이어 뱀과 초기 적 뱀 
        self.player = Snake([GRID_SIZE//2, GRID_SIZE//2], GREEN, is_player=True)
        self.snakes = [self.player]
        self.spawn_ai()  # 초기 적 뱀  

        self.foods = []

        pygame.time.set_timer(SPAWN_FOOD_EVENT, FOOD_SPAWN_INTERVAL)
        pygame.time.set_timer(SPAWN_AI_EVENT_30, 30000, loops=1)
        pygame.time.set_timer(SPAWN_AI_EVENT_60, 60000, loops=1)
        
        self.retry_rect = None
        self.quit_rect = None



    def game_over(self): # GAMEOVER 화면 구현 
        font_go = pygame.font.SysFont('times new roman', 90)
        surf_go = font_go.render('GAME OVER', True, RED)
        rect_go = surf_go.get_rect()
        rect_go.midtop = (WINDOW_WIDTH/2, WINDOW_HEIGHT/4)
        self.window.fill(BLACK)
        self.window.blit(surf_go, rect_go)

        # 최종 점수 표시
        score_font = pygame.font.SysFont('consolas', 30)
        final_score = getattr(self.player, 'score', 0)
        if final_score > self.high_score:
            self.high_score = final_score
            with open(self.SCORE_FILE, 'w') as f:
                f.write(str(self.high_score))

        surf_score = score_font.render(f'Score : {final_score}', True, WHITE)
        rect_score = surf_score.get_rect()
        rect_score.midtop = (WINDOW_WIDTH/2, WINDOW_HEIGHT*3/4)
        self.window.blit(surf_score, rect_score)
        
        pygame.display.flip()

        # Retry / Quit 대기 루프
        button_font = pygame.font.SysFont('consolas', 30)

        retry_text = button_font.render("Retry", True, WHITE)
        retry_rect = retry_text.get_rect(center=(WINDOW_WIDTH / 2 - 100, WINDOW_HEIGHT / 2))

        quit_text = button_font.render("Quit", True, WHITE)
        quit_rect = quit_text.get_rect(center=(WINDOW_WIDTH / 2 + 100, WINDOW_HEIGHT / 2))

        while True:
            self.window.fill(BLACK)
            self.window.blit(surf_go, rect_go)
            self.window.blit(surf_score, rect_score)

            pygame.draw.rect(self.window, GRAY, retry_rect.inflate(20, 10))
            pygame.draw.rect(self.window, GRAY, quit_rect.inflate(20, 10)) 

            # button text
            retry_text = button_font.render("Retry", True, RED)
            quit_text = button_font.render("Quit", True, RED)

            self.window.blit(retry_text, retry_rect)
            self.window.blit(quit_text, quit_rect)
            
            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == MOUSEBUTTONDOWN:
                    if retry_rect.collidepoint(pygame.mouse.get_pos()):
                        self.__init__()
                        self.run()
                        return
                    elif quit_rect.collidepoint(pygame.mouse.get_pos()):
                        pygame.quit()
                        sys.exit()
        
        
    def spawn_food(self):
        elapsed = pygame.time.get_ticks() - self.start_time
        available = [i for i, t in enumerate(FOOD_UNLOCK_TIMES) if elapsed >= t]
        idx = random.choice(available)
        while True:
            pos = [random.randrange(GRID_SIZE), random.randrange(GRID_SIZE)]
            if not any(pos in s.body for s in self.snakes if s.alive):
                self.foods.append(Food(pos, FOOD_SCORES[idx]))
                break

    def spawn_ai(self):
        pos = [random.randrange(GRID_SIZE), random.randrange(GRID_SIZE)]
        ai = AiSnake(pos, RED)
        self.snakes.append(ai)

    def handle_collisions(self):
        now = pygame.time.get_ticks()
        to_kill = []

        # 1) 경계 충돌 => death
        for s in self.snakes:
            if not s.alive:
                continue
            x, y = s.head_pos()
            if x < 0 or x >= GRID_SIZE or y < 0 or y >= GRID_SIZE:
                to_kill.append((s, now))

        # 2) 음식 충돌
        for s in self.snakes:
            if not s.alive:
                continue
            head = s.head_pos()
            for f in self.foods:
                if tuple(f.pos) == head:
                    s.grow()
                    if s.is_player:
                        self.player.score = getattr(self.player, 'score', 0) + f.score
                    self.foods.remove(f)
                    break

        # 3) 뱀 대 뱀 충돌
        for s1 in self.snakes:
            if not s1.alive:
                continue
            head1 = s1.head_pos()
            for s2 in self.snakes:
                if s1 is s2 or not s2.alive:
                    continue

                # head-body 충돌 (s2의 머리 제외)
                collided = False
                for segment in s2.body[1:]:
                    if tuple(segment) == head1:
                        to_kill.append((s1, now))
                        collided = True
                        break
                if collided:
                    continue
                # head-head 충돌
                if head1 == s2.head_pos():
                    if s1.length() > s2.length():
                        s1.body = s1.body[:s1.length() - s2.length()]
                        to_kill.append((s2, now))
                    elif s2.length() > s1.length():
                        s2.body = s2.body[:s2.length() - s1.length()]
                        to_kill.append((s1, now))
                    else:
                        to_kill.append((s1, now))
                        to_kill.append((s2, now))

        # 4) 플레이어 사망 시 게임 종료
        if any(s for s, _ in to_kill if s.is_player):
            self.game_over()

        # 5) 사망 적용 및 100점 먹이 등장
        for s, _ in to_kill:
            if s.alive:
                for seg in s.body:
                    self.foods.append(Food(seg[:], 100))
            s.die()

    def draw_ui(self):

        # High Score 표시: 줄 바꿈 후 점수 표시 
        label_surf = self.font.render('High Score:', True, WHITE)
        score_surf = self.font.render(f'{self.high_score}', True, WHITE)
        self.window.blit(label_surf, (10, 10))
        self.window.blit(score_surf, (10, 35))

        # 제한 시간 표시
        rem = max(0, TIME_LIMIT - (pygame.time.get_ticks() - self.start_time) / 1000)
        tm_surf = self.font.render(f'Time {rem:.1f}s', True, WHITE)
        self.window.blit(tm_surf, (self.right_offset + 10, 10))


    def run(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            now = pygame.time.get_ticks()

            # 이벤트 처리
            for ev in pygame.event.get():
                if ev.type == QUIT:
                    running = False
                elif ev.type == KEYDOWN and self.player.alive:
                    km = {K_w: 'UP', K_s: 'DOWN', K_a: 'LEFT', K_d: 'RIGHT'}
                    if ev.key in km:
                        self.player.set_direction(km[ev.key])
                    elif ev.key == K_j:
                        self.player.speed = (
                            self.player.base_speed // 2
                            if self.player.speed == self.player.base_speed
                            else self.player.base_speed
                        )
                elif ev.type == SPAWN_FOOD_EVENT:
                    self.spawn_food()
                elif ev.type == SPAWN_AI_EVENT_30 or ev.type == SPAWN_AI_EVENT_60:
                    self.spawn_ai()

            # 뱀 업데이트 및 충돌 처리
            for s in self.snakes:
                s.update(now)
            self.handle_collisions()

            # 화면 렌더링
            self.window.fill(GRAY)

            # 게임 영역 배경
            pygame.draw.rect(
                self.window, GRAY,
                (
                    self.game_offset, 0,
                    GRID_SIZE * CELL_SIZE,
                    GRID_SIZE * CELL_SIZE
                )
            )

            # 흰색 격자선
            LIGHT_GRAY = (200, 200, 200)
            for i in range(GRID_SIZE + 1):
                x = self.game_offset + i * CELL_SIZE
                pygame.draw.line(
                    self.window, LIGHT_GRAY, (x, 0), (x, WINDOW_HEIGHT)
                )
            for j in range(GRID_SIZE + 1):
                y = j * CELL_SIZE
                pygame.draw.line(
                    self.window, LIGHT_GRAY,
                    (self.game_offset, y),
                    (self.game_offset + GRID_SIZE * CELL_SIZE, y)
                )

            # 게임 영역 테두리 그리기 
            
            pygame.draw.rect(
                self.window, WHITE,
                (
                    self.game_offset, 0,
                    GRID_SIZE * CELL_SIZE,
                    GRID_SIZE * CELL_SIZE
                ),
                2
            )

            # 음식 및 뱀 그리기
            for f in self.foods:
                f.draw(self.window, self.game_offset)
            for s in self.snakes:
                s.draw(self.window, self.game_offset)

            # UI 패널
            pygame.draw.rect(
                self.window, BLACK,
                (0, 0, PANEL_WIDTH, WINDOW_HEIGHT)
            )
            pygame.draw.rect(
                self.window, BLACK,
                (self.right_offset, 0, PANEL_WIDTH, WINDOW_HEIGHT)
            )
            self.draw_ui()

            pygame.display.flip()
            clock.tick(60)

            # 제한 시간 체크
            if now - self.start_time >= TIME_LIMIT * 1000:
                self.game_over()

        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    Game().run()
