import pygame
import math
import random

# Khởi tạo Pygame
pygame.init()
WIDTH, HEIGHT = 1200, 800
win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("FPV Drone Racing Simulator")

# Màu sắc
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# Thông số drone
drone_pos = [WIDTH//2, HEIGHT//2]
drone_angle = 0
drone_speed = 0
MAX_SPEED = 10
ACCELERATION = 0.5
TURN_SPEED = 5

# Checkpoint map
checkpoints = [(200, 200), (1000, 200), (1000, 600), (200, 600)]
current_checkpoint = 0

clock = pygame.time.Clock()

def draw_drone(pos, angle):
    x, y = pos
    points = [
        (x + 20 * math.cos(math.radians(angle)), y + 20 * math.sin(math.radians(angle))),
        (x + 10 * math.cos(math.radians(angle + 140)), y + 10 * math.sin(math.radians(angle + 140))),
        (x + 10 * math.cos(math.radians(angle - 140)), y + 10 * math.sin(math.radians(angle - 140))),
    ]
    pygame.draw.polygon(win, RED, points)

def draw_map():
    for cp in checkpoints:
        pygame.draw.circle(win, BLUE, cp, 20)

run = True
while run:
    clock.tick(60)
    win.fill(WHITE)

    # Xử lý sự kiện
    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP]:
        drone_speed = min(drone_speed + ACCELERATION, MAX_SPEED)
    elif keys[pygame.K_DOWN]:
        drone_speed = max(drone_speed - ACCELERATION, -MAX_SPEED)
    else:
        drone_speed *= 0.95  # Ma sát

    if keys[pygame.K_LEFT]:
        drone_angle += TURN_SPEED
    if keys[pygame.K_RIGHT]:
        drone_angle -= TURN_SPEED

    # Update vị trí
    drone_pos[0] += drone_speed * math.cos(math.radians(drone_angle))
    drone_pos[1] += drone_speed * math.sin(math.radians(drone_angle))

    # Kiểm tra checkpoint
    cp_x, cp_y = checkpoints[current_checkpoint]
    dist = math.hypot(drone_pos[0] - cp_x, drone_pos[1] - cp_y)
    if dist < 30:
        current_checkpoint = (current_checkpoint + 1) % len(checkpoints)

    # Vẽ
    draw_map()
    draw_drone(drone_pos, drone_angle)

    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

pygame.quit()
