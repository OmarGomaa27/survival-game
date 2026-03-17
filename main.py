import pygame
import sys

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
FOG        = (10,  10,  10)

FOG_RADIUS = 3

# ── Simple fixed map (0 = floor, 1 = wall) ───────────────────
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
# ── Agent ─────────────────────────────────────────────────────
class Agent:
    def __init__(self, x, y):
        self.x = x  # grid col
        self.y = y  # grid row
        self.hp = 100

    def move(self, dx, dy):
        nx, ny = self.x + dx, self.y + dy
        if 0 <= nx < COLS and 0 <= ny < ROWS and MAP[ny][nx] == 0:
            self.x, self.y = nx, ny

    def draw(self, surface):
        rect = pygame.Rect(self.x*TILE, self.y*TILE, TILE, TILE)
        pygame.draw.rect(surface, GREEN, rect)
        # draw @ symbol
        font = pygame.font.SysFont(None, 22)
        label = font.render("@", True, WHITE)
        surface.blit(label, (self.x*TILE+10, self.y*TILE+8))

# ── Fog of War ────────────────────────────────────────────────
def draw_fog(surface, agent):
    fog_surface = pygame.Surface((W, H), pygame.SRCALPHA)
    fog_surface.fill((0, 0, 0, 240))  # near-black transparent overlay

    # cut a visible circle/square out around the agent
    for row in range(ROWS):
        for col in range(COLS):
            dist = ((col - agent.x)**2 + (row - agent.y)**2) ** 0.5  # Euclidean = circle
            if dist <= FOG_RADIUS:
                # clear this tile from the fog
                pygame.draw.rect(fog_surface, (0,0,0,0),
                                 (col*TILE, row*TILE, TILE, TILE))
    surface.blit(fog_surface, (0, 0))

# ── Draw Grid ─────────────────────────────────────────────────
def draw_map(surface):
    for row in range(ROWS):
        for col in range(COLS):
            color = GREY if MAP[row][col] == 1 else DARK_GREY
            rect = pygame.Rect(col*TILE, row*TILE, TILE, TILE)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, BLACK, rect, 1)  # grid lines

# ── HUD ───────────────────────────────────────────────────────
def draw_hud(surface, agent):
    font = pygame.font.SysFont(None, 28)
    hp_text = font.render(f"HP: {agent.hp}", True, WHITE)
    surface.blit(hp_text, (8, 8))

# ── Main Loop ─────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Survivor Roguelike Demo")
    clock = pygame.time.Clock()

    agent = Agent(x=10, y=10)  # start in the middle

    running = True
    while running:
        clock.tick(FPS)

        # ── Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:    agent.move(0, -1)
                if event.key == pygame.K_DOWN:  agent.move(0,  1)
                if event.key == pygame.K_LEFT:  agent.move(-1, 0)
                if event.key == pygame.K_RIGHT: agent.move(1,  0)
                if event.key == pygame.K_ESCAPE: running = False

        # ── Draw
        screen.fill(BLACK)
        draw_map(screen)
        agent.draw(screen)
        draw_fog(screen, agent)
        draw_hud(screen, agent)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()