import pygame
import sys
from game.enemy import spawn_enemies

# ── Constants ────────────────────────────────────────────────
TILE = 24
FPS = 10

# Colors
BLACK      = (0,   0,   0)
DARK_GREY  = (30,  30,  30)
GREY       = (60,  60,  60)
WHITE      = (255, 255, 255)
GREEN      = (50,  200, 50)
RED        = (200, 50,  50)
YELLOW     = (255, 220, 0)

FOG_RADIUS = 3

# ── Map (0 = floor, 1 = wall) ───────────────────────────────
MAP = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,0,0,1],
    [1,0,0,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,1,1,1,0,0,0,0,1,1,1,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,1,1],
    [1,1,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,1,1,1,0,0,0,0,1,1,1,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1],
    [1,0,0,1,1,0,0,0,0,0,0,0,0,1,1,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]

ROWS = len(MAP)
COLS = len(MAP[0])
W = COLS * TILE
H = ROWS * TILE

# ── Agent ────────────────────────────────────────────────────
class Agent:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hp = 100

    def move(self, dx, dy):
        nx, ny = self.x + dx, self.y + dy
        if 0 <= nx < COLS and 0 <= ny < ROWS and MAP[ny][nx] == 0:
            self.x, self.y = nx, ny

    def draw(self, surface, font):
        rect = pygame.Rect(self.x * TILE, self.y * TILE, TILE, TILE)
        pygame.draw.rect(surface, GREEN, rect)
        label = font.render("@", True, WHITE)
        surface.blit(label, (self.x * TILE + 8, self.y * TILE + 6))


# ── Fog of War ───────────────────────────────────────────────
def draw_fog(surface, agent):
    fog_surface = pygame.Surface((W, H), pygame.SRCALPHA)
    fog_surface.fill((0, 0, 0, 240))

    for row in range(ROWS):
        for col in range(COLS):
            dist = ((col - agent.x) ** 2 + (row - agent.y) ** 2) ** 0.5
            if dist <= FOG_RADIUS:
                pygame.draw.rect(
                    fog_surface,
                    (0, 0, 0, 0),
                    (col * TILE, row * TILE, TILE, TILE)
                )

    surface.blit(fog_surface, (0, 0))


# ── Draw Grid ────────────────────────────────────────────────
def draw_map(surface):
    for row in range(ROWS):
        for col in range(COLS):
            color = GREY if MAP[row][col] == 1 else DARK_GREY
            rect = pygame.Rect(col * TILE, row * TILE, TILE, TILE)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, BLACK, rect, 1)


# ── HUD ──────────────────────────────────────────────────────
def draw_hud(surface, agent, wave, kills):
    font = pygame.font.SysFont(None, 28)
    hp_text = font.render(f"HP: {agent.hp}", True, WHITE)
    wave_text = font.render(f"Wave: {wave}", True, WHITE)
    kills_text = font.render(f"Kills: {kills}", True, WHITE)

    surface.blit(hp_text, (8, 8))
    surface.blit(wave_text, (8, 32))
    surface.blit(kills_text, (8, 56))


# ── Main Loop ────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Survival Roguelike Demo")
    clock = pygame.time.Clock()

    tile_font = pygame.font.SysFont(None, 22)

    agent = Agent(x=10, y=10)

    # game state
    tick_count = 0
    wave = 1
    kills = 0
    enemies = spawn_enemies(5, COLS, ROWS, agent)

    running = True
    while running:
        clock.tick(FPS)

        # ── Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    agent.move(0, -1)
                elif event.key == pygame.K_DOWN:
                    agent.move(0, 1)
                elif event.key == pygame.K_LEFT:
                    agent.move(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    agent.move(1, 0)
                elif event.key == pygame.K_ESCAPE:
                    running = False

        # ── Enemy tick
        tick_count += 1
        if tick_count % 2 == 0:
            for e in list(enemies):
                e.step_toward_agent(agent, MAP)

                # enemy reaches agent
                if e.x == agent.x and e.y == agent.y:
                    agent.hp -= e.damage
                    enemies.remove(e)

                    if agent.hp <= 0:
                        print(f"Agent died! Kills: {kills}")
                        running = False
                        break

        # respawn next wave when all enemies are gone
        if len(enemies) == 0 and running:
            wave += 1
            enemies = spawn_enemies(5 + wave * 2, COLS, ROWS, agent)
            print(f"Wave {wave} started — {len(enemies)} enemies")

        # ── Draw
        screen.fill(BLACK)
        draw_map(screen)

        for e in enemies:
            if e.alive:
                e.draw(screen, TILE, tile_font)

        agent.draw(screen, tile_font)
        draw_fog(screen, agent)
        draw_hud(screen, agent, wave, kills)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()