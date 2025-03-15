from typing import List
from threading import Thread
from queue import Queue
import sys
import os

import pygame

from game_graphics import GameGraphics
from connect4_AMAF import GameBoard, AMAF, Node

# Screen resolution
WIN_SIZE = (W_WIDTH, W_HEIGHT) = (800, 600)

# AMAF move computation time
PROCESS_TIME =  5

# Frame rate
FPS = 30



if __name__ == "__main__":
    # Initialize pygame
    os.system("cls")
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_caption("Connect 4 Montecarlo with AMAF")
    window = pygame.display.set_mode(WIN_SIZE)
    clock = pygame.time.Clock()
    graphics = GameGraphics(win_size=WIN_SIZE, surface=window)

    # Begin new game
    while True:
        gameboard = GameBoard(cpu=1)
        amaf = AMAF(symbol=1, t=5)
        game_over = False
        winner_id = None
        select_move = 1

        # Game loop
        while True:
            # Check for game over
            game_over, winner_id = gameboard.check_win()
            if game_over:
                pygame.time.wait(1000)
                break

            # Draw game graphics
            graphics.draw_background(speed=100)
            graphics.draw_board(gameboard.board)
            graphics.draw_select(select_move, gameboard.turn)

            # Update display
            clock.tick(FPS)
            pygame.event.pump()
            pygame.display.flip()

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        sys.exit()
                    elif event.key == pygame.K_RIGHT:
                        if select_move < 7:
                            select_move += 1
                    elif event.key == pygame.K_LEFT:
                        if select_move > 1:
                            select_move -= 1
                    elif event.key == pygame.K_RETURN:
                        if gameboard.turn != amaf.symbol:  
                            if gameboard.board[5, select_move - 1] == 0:
                                gameboard.apply_move(select_move)

            # AMAF turn
            if gameboard.turn == amaf.symbol: 
                root = Node(parent=None, board=gameboard.board, turn=amaf.symbol)
                amaf_move = amaf.compute_move(root)
                if amaf_move != (-1, -1):
                    gameboard.apply_move(amaf_move[1] + 1)  
        # Game over / continue
        select_option = 1
        new_game = False
        while not new_game:
            # Menu controls
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        sys.exit()
                    elif event.key == pygame.K_RIGHT:
                        if select_option < 2:
                            select_option += 1
                    elif event.key == pygame.K_LEFT:
                        if select_option > 1:
                            select_option -= 1
                    elif event.key == pygame.K_RETURN:
                        if select_option == 1:
                            new_game = True
                        elif select_option == 2:
                            sys.exit()

            # Draw game over screen
            graphics.draw_background(speed=100)
            graphics.gameover_screen(winner_id, select_option)

            # Update display
            clock.tick(FPS)
            pygame.event.pump()
            pygame.display.flip()