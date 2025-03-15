from typing import Tuple, List, Optional
import random
import time
import os
import sys
import numpy as np
import pygame
from game_graphics import GameGraphics, WIN_SIZE, FPS




class GameBoard:
    """Connect4 game board class."""

    def __init__(self, cpu: int) -> None:
        self.turn = random.randint(1, 2)
        self.board = np.zeros(shape=(6, 7))
        self.cpu = cpu

    def check_win(self) -> Tuple[bool, Optional[int]]:
        """Check whether the match is over.

        Returns:
            Tuple[bool, int | None]: Game has ended, winner id or None.
        """
        winner = GameBoard.check_rows(self.board)
        if winner is not None:
            return (True, winner)

        winner = GameBoard.check_cols(self.board)
        if winner is not None:
            return (True, winner)

        winner = GameBoard.check_diag(self.board)
        if winner is not None:
            return (True, winner)

        if GameBoard.check_tie(self.board):
            return (True, None)

        return (False, None)

    @staticmethod
    def check_rows(board: np.ndarray) -> Optional[int]:
        """Check for winner in rows."""
        for y in range(6):
            row = list(board[y, :])
            for x in range(4):
                if row[x : x + 4].count(row[x]) == 4:
                    if row[x] != 0:
                        return row[x]
        return None

    @staticmethod
    def check_cols(board: np.ndarray) -> Optional[int]:
        """Check for winner in columns."""
        for x in range(7):
            col = list(board[:, x])
            for y in range(3):
                if col[y : y + 4].count(col[y]) == 4:
                    if col[y] != 0:
                        return col[y]
        return None

    @staticmethod
    def check_diag(board: np.ndarray) -> Optional[int]:
        """Check for winner in diagonals."""
        # Right diagonal
        for point in [
            (3, 0), (4, 0), (3, 1), (5, 0), (4, 1), (3, 2), (5, 1), (4, 2),
            (3, 3), (5, 2), (4, 3), (5, 3)
        ]:
            diag = []
            for k in range(4):
                diag.append(board[point[0] - k, point[1] + k])
            if diag.count(1) == 4 or diag.count(2) == 4:
                return diag[0]
        # Left diagonal
        for point in [
            (5, 3), (5, 4), (4, 3), (5, 5), (4, 4), (3, 3), (5, 6), (4, 5),
            (3, 4), (4, 6), (3, 5), (3, 6)
        ]:
            diag = []
            for k in range(4):
                diag.append(board[point[0] - k, point[1] - k])
            if diag.count(1) == 4 or diag.count(2) == 4:
                return diag[0]
        return None

    @staticmethod
    def check_tie(board: np.ndarray) -> bool:
        """Check if board is a tie."""
        return bool(np.all(board != 0)) and not GameBoard.check_rows(board) and not GameBoard.check_cols(board) and not GameBoard.check_diag(board)

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
        if self.turn == 1:
            self.turn = 2
        else:
            self.turn = 1


class RAVE:
    """Monte Carlo Tree search class with RAVE."""

    def __init__(self, symbol: int, t: float) -> None:
        self.symbol = symbol
        self.t = t

    def compute_move(self, node: "Node") -> Tuple[int, int]:
        """Compute move using MCTS algorithm with RAVE."""
        time0 = time.time()
        while (time.time() - time0) < self.t:
            # Selection and expansion
            leaf = self.select(node)
            if leaf is None:
                return (-1, -1)
            # Simulation
            simulation_result, actions = self.rollout(leaf)
            # Backpropagation
            self.backpropagate(leaf, simulation_result, actions)
        # From next best state, get move coordinates
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
            tmp = self.select_uct(node)
            if tmp == node:
                break
            node = tmp
        if node.terminal:
            return node
        node.add_child()
        if node.children:
            return self.pick_unvisited(node.children)
        return node

    def select_uct(self, node: "Node") -> "Node":
        """Select node with best UCT value, including RAVE."""
        best_uct = -np.inf
        best_node = None
        for child in node.children:
            # Classic UCT value
            uct = (child.q / child.n) + 2 * np.sqrt(np.log(node.n) / child.n)
            # RAVE value
            beta = np.sqrt(self.t / (3 * node.n + self.t))  # Weight for RAVE
            rave_value = (child.rave_q / child.rave_n) if child.rave_n > 0 else 0
            # Combined value
            combined_value = (1 - beta) * uct + beta * rave_value
            if combined_value > best_uct:
                best_uct = combined_value
                best_node = child
        if best_node is None:
            return node
        return best_node

    def fully_expanded(self, node: "Node") -> bool:
        """Check whether a node is fully expanded."""
        visited = True
        if list(node.board[5]).count(0) == len(node.children):
            for child in node.children:
                if child.n == 0:
                    visited = False
            return visited
        return False

    def pick_unvisited(self, children: List["Node"]) -> Optional["Node"]:
        """Pick first unexplored child node."""
        for child in children:
            if child.n == 0:
                return child
        return None

    def rollout(self, node: "Node") -> Tuple[Optional[int], List[Tuple[int, int]]]:
        """Perform a random game simulation and record actions for RAVE."""
        board = node.board
        turn = node.turn
        actions = []  # Store actions taken during the rollout
        if not node.terminal:
            while True:
                turn = 1 if turn == 2 else 2
                moves = self.get_moves(board, turn)
                if moves:
                    next_board = random.choice(moves)
                    action = self.get_action(board, next_board)
                    if action is not None:
                        actions.append(action)
                    board = next_board
                    terminal = self.result(board)
                    if terminal != 0:
                        return terminal, actions
                else:
                    return self.result(board), actions
        else:
            return self.result(board), actions

    def get_moves(self, board: np.ndarray, turn: int) -> List[np.ndarray]:
        """Get all possible next states."""
        moves = []
        for i in range(7):
            if board[5, i] == 0:
                for j in range(6):
                    if board[j, i] == 0:
                        tmp = board.copy()
                        tmp[j, i] = turn
                        moves.append(tmp)
                        break
        return moves

    def result(self, board: np.ndarray) -> Optional[int]:
        """Get game result from terminal board."""
        winner = GameBoard.check_rows(board)
        if winner is not None:
            return winner
        winner = GameBoard.check_cols(board)
        if winner is not None:
            return winner
        winner = GameBoard.check_diag(board)
        if winner is not None:
            return winner
        return None

    def backpropagate(self, node: "Node", winner: Optional[int], actions: List[Tuple[int, int]]) -> None:
        """Update recursively node visits and scores from leaf to root, including RAVE."""
        if node.turn == winner:
            node.q += 1
        node.n += 1
        # Update RAVE statistics for all actions in the simulation
        for action in actions:
            for child in node.children:
                if (child.board[action[0], action[1]] != node.board[action[0], action[1]]):
                    child.rave_q += (1 if node.turn == winner else 0)
                    child.rave_n += 1
        if node.parent is None:
            return
        self.backpropagate(node.parent, winner, actions)

    def best_child(self, node: "Node") -> Optional["Node"]:
        """Get child node with largest number of visits."""
        max_visit = 0
        best_node = None
        for child in node.children:
            if child.n > max_visit:
                max_visit = child.n
                best_node = child
        return best_node

    def get_action(self, parent_board: np.ndarray, child_board: np.ndarray) -> Optional[Tuple[int, int]]:
        """Get the action (row, col) that led from parent_board to child_board."""
        for j in range(6):
            for i in range(7):
                if parent_board[j, i] != child_board[j, i]:
                    return (j, i)
        return None


class Node:
    """Monte Carlo tree node class with RAVE."""

    def __init__(
        self, parent: Optional["Node"], board: np.ndarray, turn: int
    ) -> None:
        self.q = 0  # sum of rollout outcomes
        self.n = 0  # number of visits
        self.rave_q = 0  # sum of RAVE outcomes for this action
        self.rave_n = 0  # number of RAVE visits for this action
        self.parent = parent
        self.board = board
        if turn == 1:
            self.turn = 2
        else:
            self.turn = 1
        self.children: List["Node"] = []
        self.terminal = self.check_terminal()
        self.expanded = False

    def check_terminal(self) -> bool:
        """Check whether node is a leaf."""
        if GameBoard.check_rows(self.board):
            return True
        if GameBoard.check_cols(self.board):
            return True
        if GameBoard.check_diag(self.board):
            return True
        if GameBoard.check_tie(self.board):
            return True
        return False

    def add_child(self) -> None:
        """Add new child to node."""
        if self.expanded:
            return
        child_board = []
        for child in self.children:
            child_board.append(child.board)
        for i in range(7):
            if self.board[5, i] == 0:
                for j in range(6):
                    if self.board[j, i] == 0:
                        tmp = self.board.copy()
                        if self.turn == 1:
                            tmp[j, i] = 2
                            if child_board:
                                if not self.compare_children(tmp, child_board):
                                    self.children.append(Node(self, tmp, 1))
                                    return
                                break
                            self.children.append(Node(self, tmp, 1))
                            return
                        else:
                            tmp[j, i] = 1
                            if child_board:
                                if not self.compare_children(tmp, child_board):
                                    self.children.append(Node(self, tmp, 2))
                                    return
                                break
                            self.children.append(Node(self, tmp, 2))
                            return
        self.expanded = True
        return

    def compare_children(
        self, new_child: np.ndarray, children: List[np.ndarray]
    ) -> bool:
        """Check if node state is equal to one of children state."""
        for child in children:
            if (new_child == child).all():
                return True
        return False


