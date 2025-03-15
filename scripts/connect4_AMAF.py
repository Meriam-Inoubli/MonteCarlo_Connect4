from typing import Tuple, List, Optional, Dict
import random
import time
import os
import sys
import numpy as np
import pygame
from game_graphics import GameGraphics, WIN_SIZE, FPS

# MCTS move computation time
PROCESS_TIME: float = 3.0


class GameBoard:
    """Connect4 game board class."""

    def __init__(self, cpu: int) -> None:
        self.turn = random.randint(1, 2)
        self.board = np.zeros(shape=(6, 7))
        self.cpu = cpu

    def check_win(self) -> Tuple[bool, Optional[int]]:
        """Check whether the match is over."""
        for check in [self.check_rows, self.check_cols, self.check_diag]:
            winner = check(self.board)
            if winner is not None:
                return (True, winner)
        if self.check_tie(self.board):
            return (True, None)
        return (False, None)

    @staticmethod
    def check_rows(board: np.ndarray) -> Optional[int]:
        """Check for winner in rows."""
        for y in range(6):
            for x in range(4):
                if board[y, x] == board[y, x + 1] == board[y, x + 2] == board[y, x + 3] != 0:
                    return board[y, x]
        return None

    @staticmethod
    def check_cols(board: np.ndarray) -> Optional[int]:
        """Check for winner in columns."""
        for x in range(7):
            for y in range(3):
                if board[y, x] == board[y + 1, x] == board[y + 2, x] == board[y + 3, x] != 0:
                    return board[y, x]
        return None

    @staticmethod
    def check_diag(board: np.ndarray) -> Optional[int]:
        """Check for winner in diagonals."""
        # Right diagonal
        for y in range(3):
            for x in range(4):
                if board[y, x] == board[y + 1, x + 1] == board[y + 2, x + 2] == board[y + 3, x + 3] != 0:
                    return board[y, x]
        # Left diagonal
        for y in range(3):
            for x in range(3, 7):
                if board[y, x] == board[y + 1, x - 1] == board[y + 2, x - 2] == board[y + 3, x - 3] != 0:
                    return board[y, x]
        return None

    @staticmethod
    def check_tie(board: np.ndarray) -> bool:
        """Check if board is a tie."""
        return np.all(board != 0)

    def apply_move(self, column: int) -> bool:
        """Apply move to board."""
        for i in range(6):
            if self.board[i, column - 1] == 0:
                self.board[i, column - 1] = self.turn
                self.switch_turn()
                return True
        return False

    def switch_turn(self) -> None:
        """Switch turn between players."""
        self.turn = 3 - self.turn  # Switch between 1 and 2


class AMAF:
    """All Moves As First (AMAF) class."""

    def __init__(self, symbol: int, t: float) -> None:
        self.symbol = symbol
        self.t = t
        self.amaf_stats: Dict[Tuple[int, int], Tuple[int, int]] = {}  

    def compute_move(self, node: "Node") -> Tuple[int, int]:
        """Compute move using AMAF algorithm."""
        time0 = time.time()
        while (time.time() - time0) < self.t:
            leaf = self.select(node)
            if leaf is None:
                return (-1, -1)
            simulation_result, actions = self.rollout(leaf)
            self.backpropagate(leaf, simulation_result, actions)
        selected = self.best_child(node)
        if selected is None:
            return (-1, -1)
        for j in range(6):
            for i in range(7):
                if selected.board[j][i] != node.board[j][i]:
                    return (j, i)
        return (-1, -1)

    def select(self, node: "Node") -> Optional["Node"]:
        """Node selection and expansion phase."""
        while self.fully_expanded(node):
            tmp = self.select_amaf(node)
            if tmp == node:
                break
            node = tmp
        if node.terminal:
            return node
        node.add_child()
        if node.children:
            return self.pick_unvisited(node.children)
        return node

    def select_amaf(self, node: "Node") -> "Node":
        """Select node with best AMAF value."""
        best_value = -np.inf
        best_node = None
        for child in node.children:
            # Classic UCT value
            uct = (child.q / child.n) + 2 * np.sqrt(np.log(node.n) / child.n)
            # AMAF value
            amaf_value = self.get_amaf_value(child)
            # Combined value
            combined_value = uct + amaf_value
            if combined_value > best_value:
                best_value = combined_value
                best_node = child
        return best_node if best_node is not None else node

    def get_amaf_value(self, child: "Node") -> float:
        """Get AMAF value for a child node."""
        action = self.get_action(child.parent.board, child.board)
        if action is None:
            return 0
        q, n = self.amaf_stats.get(action, (0, 0))
        return q / n if n > 0 else 0

    def fully_expanded(self, node: "Node") -> bool:
        """Check whether a node is fully expanded."""
        return all(child.n > 0 for child in node.children) if len(node.children) == list(node.board[5]).count(0) else False

    def pick_unvisited(self, children: List["Node"]) -> Optional["Node"]:
        """Pick first unexplored child node."""
        return next((child for child in children if child.n == 0), None)

    def rollout(self, node: "Node") -> Tuple[Optional[int], List[Tuple[int, int]]]:
        """Perform a random game simulation and record actions for AMAF."""
        board, turn, actions = node.board, node.turn, []
        while not node.terminal:
            turn = 3 - turn
            moves = self.get_moves(board, turn)
            if not moves:
                break
            next_board = random.choice(moves)
            action = self.get_action(board, next_board)
            if action is not None:
                actions.append(action)
            board = next_board
            terminal = self.result(board)
            if terminal != 0:
                return terminal, actions
        return self.result(board), actions

    def get_moves(self, board: np.ndarray, turn: int) -> List[np.ndarray]:
        """Get all possible next states."""
        return [self.apply_move_to_board(board, i, turn) for i in range(7) if board[5, i] == 0]

    @staticmethod
    def apply_move_to_board(board: np.ndarray, col: int, turn: int) -> np.ndarray:
        """Apply a move to the board and return the new board."""
        new_board = board.copy()
        for j in range(6):
            if new_board[j, col] == 0:
                new_board[j, col] = turn
                break
        return new_board

    def result(self, board: np.ndarray) -> Optional[int]:
        """Get game result from terminal board."""
        for check in [GameBoard.check_rows, GameBoard.check_cols, GameBoard.check_diag]:
            winner = check(board)
            if winner is not None:
                return winner
        return None

    def backpropagate(self, node: "Node", winner: Optional[int], actions: List[Tuple[int, int]]) -> None:
        """Update recursively node visits and scores from leaf to root, including AMAF."""
        if node.turn == winner:
            node.q += 1
        node.n += 1
        # Update AMAF statistics for all actions in the simulation
        for action in actions:
            q, n = self.amaf_stats.get(action, (0, 0))
            q += 1 if node.turn == winner else 0
            n += 1
            self.amaf_stats[action] = (q, n)
        if node.parent is not None:
            self.backpropagate(node.parent, winner, actions)

    def best_child(self, node: "Node") -> Optional["Node"]:
        """Get child node with largest number of visits."""
        return max(node.children, key=lambda child: child.n, default=None)

    @staticmethod
    def get_action(parent_board: np.ndarray, child_board: np.ndarray) -> Optional[Tuple[int, int]]:
        """Get the action (row, col) that led from parent_board to child_board."""
        for j in range(6):
            for i in range(7):
                if parent_board[j, i] != child_board[j, i]:
                    return (j, i)
        return None


class Node:
    """Monte Carlo tree node class with AMAF."""

    def __init__(self, parent: Optional["Node"], board: np.ndarray, turn: int) -> None:
        self.q = 0  # sum of rollout outcomes
        self.n = 0  # number of visits
        self.parent = parent
        self.board = board
        self.turn = 3 - turn  # Switch turn
        self.children: List["Node"] = []
        self.terminal = self.check_terminal()
        self.expanded = False

    def check_terminal(self) -> bool:
        """Check whether node is a leaf."""
        return any(check(self.board) for check in [GameBoard.check_rows, GameBoard.check_cols, GameBoard.check_diag]) or GameBoard.check_tie(self.board)

    def add_child(self) -> None:
        """Add new child to node."""
        if self.expanded:
            return
        for i in range(7):
            if self.board[5, i] == 0:
                for j in range(6):
                    if self.board[j, i] == 0:
                        tmp = self.board.copy()
                        tmp[j, i] = self.turn
                        if not any((tmp == child.board).all() for child in self.children):
                            self.children.append(Node(self, tmp, self.turn))
                            return
                        break
        self.expanded = True


