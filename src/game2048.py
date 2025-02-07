from game2048_ui import Ui_MainWindow
from PyQt6.QtCore import pyqtSignal, QRect, QThread, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import product
import math
import numpy as np
import random
import sys
import util

FRAME_COUNT = 10
FONT = QFont(QFont().family(), 40, QFont.Weight.Bold)

GROOVE_SIZE, GAP_SIZE = 100, 15
PIECE_SIZE = GROOVE_SIZE + GAP_SIZE
GROOVE = {(i, j): (j * PIECE_SIZE + GAP_SIZE, i * PIECE_SIZE + GAP_SIZE) for i, j in product(range(4), repeat=2)}
CANVAS_SIZE = PIECE_SIZE * 4 + GAP_SIZE
WINDOW_SIZE = CANVAS_SIZE + 18, CANVAS_SIZE + 20

COLOR_SKELETON = QColor(187, 173, 160)
COLOR_NUM = QColor(118, 110, 101)
COLOR = {
	0: QColor(205, 193, 180), 2: QColor(238, 228, 218), 4: QColor(237, 224, 200), 8: QColor(242, 177, 121),
	16: QColor(245, 149, 99), 32: QColor(246, 124, 95), 64: QColor(246, 94, 59), 128: QColor(237, 207, 114),
	256: QColor(237, 204, 97), 512: QColor(228, 192, 42), 1024: QColor(226, 186, 19), 2048: QColor(236, 196, 0)
}

KEYS = {Qt.Key.Key_Left: "L", Qt.Key.Key_Right: "R", Qt.Key.Key_Up: "U", Qt.Key.Key_Down: "D"}
ROTATE = {"L": 0, "R": 2, "U": 1, "D": -1}
TRANS = {"L": lambda x, y: (x, y), "R": lambda x, y: (3 - x, 3 - y), "U": lambda x, y: (y, 3 - x), "D": lambda x, y: (3 - y, x)}


class MyCore(QMainWindow, Ui_MainWindow):
	board = np.zeros((4, 4), dtype=int)
	skeleton = None
	my_thread = None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../game2048/2048"))

		self.timer = QTimer()
		self.timer.setInterval(15)
		util.cast(self.timer).timeout.connect(self.draw)

		self.skeleton = QPixmap(CANVAS_SIZE, CANVAS_SIZE)
		self.skeleton.fill(COLOR_SKELETON)
		with QPainter(self.skeleton) as painter:
			painter.setPen(Qt.PenStyle.NoPen)
			painter.setBrush(COLOR[0])
			for pos in GROOVE.values():
				painter.drawRect(QRect(*pos, GROOVE_SIZE, GROOVE_SIZE))
		self.label.setPixmap(self.skeleton)
		self.statusbar.showMessage("按 Enter 重新开始")
		self.restart()

	def restart(self):
		self.board.fill(0)
		self.board = MyCore.add(self.board, 2)
		self.board = MyCore.add(self.board, 2)
		self.display()

	def keyPressEvent(self, a0):
		if a0.key() == Qt.Key.Key_F6:
			self.test()
			return

		if self.timer.isActive():
			return
		if a0.key() == Qt.Key.Key_Return:
			return self.restart()
		if a0.key() not in KEYS:
			return
		
		movement = KEYS[util.cast(a0.key())]
		self.board, trails = MyCore.moving(self.board, movement)

		self.timer.setProperty("frame", 0)
		self.timer.setProperty("trails", trails)
		self.timer.start()

		if 2048 in self.board:
			util.dialog("You win", "success")
			return self.restart()
		if MyCore.lose(self.board):
			util.dialog("You lose", "error")
			return self.restart()

	def test(self):
		self.my_thread = MyThread()
		self.my_thread.start()


	@staticmethod
	def moving(board, movement):
		previous = board.copy()
		rotate = ROTATE[movement]
		trans = TRANS[movement]

		board = np.rot90(board, rotate)
		board, trails = MyCore.merge(board, trans)
		board = np.rot90(board, -rotate)

		if 2048 not in board and board.tolist() != previous.tolist():
			board = MyCore.add(board)
		return board, trails

	@staticmethod
	def merge(board, trans):
		following, merged, trails = [[] for _ in range(4)], [False] * 4, []
		for i, j in product(range(4), repeat=2):
			tile = board[i, j]
			if not tile:
				continue
			if following[i] and following[i][-1] == tile and not merged[i]:
				following[i][-1] *= 2
				merged[i] = True
			else:
				following[i].append(tile)
				merged[i] = False
			trails.insert(0, [trans(i, j), trans(i, len(following[i]) - 1), tile])
		board = np.array([f + [0] * (4 - len(f)) for f in following])
		return board, trails
	
	@staticmethod
	def add(board, tile=None):
		if tile is None:
			tile = 2 if random.random() < 0.9 else 4
		empty_cells = np.argwhere(board == 0)
		board[tuple(random.choice(empty_cells))] = tile
		return board

	@staticmethod
	def lose(board):
		return 0 not in board and not any(0 in np.diff(f) for f in np.concatenate((board, board.T)))

	def display(self):
		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(FONT)
			for f, pos in GROOVE.items():
				self.dye(painter, self.board[f], pos)
		self.label.setPixmap(pixmap)

	def draw(self):
		self.timer.setProperty("frame", self.timer.property("frame") + 1)
		if self.timer.property("frame") > FRAME_COUNT:
			self.timer.stop()
			return self.display()

		offset = self.timer.property("frame") / FRAME_COUNT
		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(FONT)
			for start, end, tile in self.timer.property("trails"):
				(sx, sy), (ex, ey) = GROOVE[start], GROOVE[end]
				pos = int(sx + (ex - sx) * offset), int(sy + (ey - sy) * offset)
				self.dye(painter, tile, pos)
		self.label.setPixmap(pixmap)

	@staticmethod
	def dye(painter, tile, pos):
		rect = QRect(*pos, GROOVE_SIZE, GROOVE_SIZE)
		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(COLOR[tile])
		painter.drawRect(rect)
		painter.setPen(COLOR_NUM)
		painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(tile).strip("0"))


class Algorithm:
	@staticmethod
	def evaluate(board):
		empty_count = np.sum(board == 0)
		max_tile = np.max(board)
		corner_priority = max_tile in (board[0, 0], board[0, 3], board[3, 0], board[3, 3])

		monotonicity = 0
		for row in np.concatenate((board, board.T)):
			dif = np.diff(row[row != 0])
			monotonicity += all(dif >= 0) or all(dif <= 0)

		merge_potential = 0
		for i, j in product(range(4), repeat=2):
			if not board[i, j]:
				continue
			if i and board[i, j] == board[i - 1, j]:
				merge_potential += 1
			if j and board[i, j] == board[i, j - 1]:
				merge_potential += 1

		return empty_count * 2 + math.log2(max_tile) * 5 + corner_priority * 5 + monotonicity + merge_potential

	@staticmethod
	def expectimax(board, depth):
		if not depth or MyCore.lose(board):
			return Algorithm.evaluate(board)

		if depth % 2:
			score = -np.inf
			for movement in ROTATE.keys():
				subsequent, _ = MyCore.moving(board, movement)
				if board.tolist() != subsequent.tolist():
					score = max(score, Algorithm.expectimax(subsequent, depth - 1))
			return score
		else:
			score = 0
			empty_cells = np.argwhere(board == 0)
			if not empty_cells.tolist():
				return Algorithm.evaluate(board)

			for empty_cell in empty_cells:
				for tile, prob in {2: 0.9, 4: 0.1}.items():
					subsequent = board.copy()
					subsequent[tuple(empty_cell)] = tile
					score += prob * Algorithm.expectimax(subsequent, depth - 1)
			return score / len(empty_cells)

	@staticmethod
	def infer(board):
		best_score = -np.inf,
		best_movement = None
		for movement in ROTATE.keys():
			subsequent, _ = MyCore.moving(board, movement)
			if board.tolist() != subsequent.tolist():
				score = Algorithm.expectimax(subsequent, 3)
				if score > best_score:
					best_score = score
					best_movement = movement
		return best_movement


class MyThread(QThread):
	signal_update = pyqtSignal()
	signal_finish = pyqtSignal(str, str)

	def __init__(self):
		super().__init__()
		util.cast(self.signal_update).connect(self.update)
		util.cast(self.signal_finish).connect(self.finish)

	def run(self):
		my_core.restart()
		while True:
			if 2048 in my_core.board:
				return util.cast(self.signal_finish).emit("You win", "success")
			if MyCore.lose(my_core.board):
				return util.cast(self.signal_finish).emit("You lose", "error")
			util.cast(self.signal_update).emit()
			self.msleep(50)

	@staticmethod
	def update():
		movement = Algorithm.infer(my_core.board)
		my_core.board, _ = MyCore.moving(my_core.board, movement)
		my_core.display()

	@staticmethod
	def finish(msg, msg_type):
		util.dialog(msg, msg_type)
		my_core.restart()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(*WINDOW_SIZE)
	my_core.show()
	sys.exit(app.exec())
