#!/usr/bin/python3.4
# Setup Python ----------------------------------------------- #
import pygame, sys, os

# Setup pygame/window ---------------------------------------- #
mainClock = pygame.time.Clock()
from pygame.locals import *
pygame.init()
pygame.display.set_caption('game base')
screen = pygame.display.set_mode((500, 500),0,32)

for img in os.listdir():
    if img[-3:] == 'png':
        i = pygame.image.load(img).convert_alpha()
        for y in range(i.get_height()):
            for x in range(i.get_width()):
                i.set_at((x, y), (255, 0, 255, 255))
        #pygame.image.save(i, img)

# Loop ------------------------------------------------------- #
while True:
    
    # Background --------------------------------------------- #
    screen.fill((0,0,0))
    
    # Buttons ------------------------------------------------ #
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()
                
    # Update ------------------------------------------------- #
    pygame.display.update()
    mainClock.tick(60)
    
