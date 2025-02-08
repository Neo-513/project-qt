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

FONT = QFont(QFont().family(), 40, QFont.Weight.Bold)
GROOVE = {(i, j): (j * 115 + 15, i * 115 + 15) for i, j in product(range(4), repeat=2)}

MOVEMENT = {Qt.Key.Key_Left: "L", Qt.Key.Key_Right: "R", Qt.Key.Key_Up: "U", Qt.Key.Key_Down: "D"}
ROTATE = {"L": 0, "R": 2, "U": 1, "D": -1}
TRANS = {"L": lambda x, y: (x, y), "R": lambda x, y: (3 - x, 3 - y), "U": lambda x, y: (y, 3 - x), "D": lambda x, y: (3 - y, x)}

COLOR = {
	0: QColor(205, 193, 180), 2: QColor(238, 228, 218), 4: QColor(237, 224, 200), 8: QColor(242, 177, 121),
	16: QColor(245, 149, 99), 32: QColor(246, 124, 95), 64: QColor(246, 94, 59), 128: QColor(237, 207, 114),
	256: QColor(237, 204, 97), 512: QColor(228, 192, 42), 1024: QColor(226, 186, 19), 2048: QColor(236, 196, 0),
	"skeleton": QColor(187, 173, 160), "tile": QColor(118, 110, 101)
}


class MyCore(QMainWindow, Ui_MainWindow):
	board = np.zeros((4, 4), dtype=int)
	skeleton, my_thread, mouse_pos = None, None, None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../game2048/2048"))

		util.button(self.pushButton, self.restart)
		util.button(self.toolButton_hinting, self.hinting, "../game2048/bulb", tip="提示", ico_size=24)
		util.button(self.toolButton_botting, self.botting, "../game2048/brain", tip="AI托管", ico_size=24)
		self.label.mousePressEvent = self.mouse_press
		self.label.mouseReleaseEvent = self.mouse_release

		self.timer = QTimer()
		self.timer.setInterval(15)
		util.cast(self.timer).timeout.connect(self.draw)

		self.skeleton = QPixmap(self.label.minimumSize())
		self.skeleton.fill(COLOR["skeleton"])
		with QPainter(self.skeleton) as painter:
			painter.setPen(Qt.PenStyle.NoPen)
			painter.setBrush(COLOR[0])
			for groove in GROOVE.values():
				painter.drawRect(QRect(*groove, 100, 100))
		self.label.setPixmap(self.skeleton)
		self.restart()

	def restart(self):
		if self.my_thread:
			self.toolButton_botting.setIcon(util.icon("../game2048/brain"))
			self.toolButton_botting.setToolTip("AI托管")
			self.my_thread.terminate()
			self.my_thread = None
		self.board.fill(0)
		self.board = MyQ.add(self.board)
		self.board = MyQ.add(self.board)
		self.display()

	def step(self, movement):
		self.board, trails = MyQ.moving(self.board, movement)

		self.timer.setProperty("frame", 0)
		self.timer.setProperty("trails", trails)
		self.timer.start()

		if MyQ.win(self.board):
			util.dialog("You win", "success")
			return self.restart()
		if MyQ.lose(self.board):
			util.dialog("You lose", "error")
			return self.restart()

	def keyPressEvent(self, a0):
		if self.timer.isActive():
			return
		if self.my_thread:
			return
		if a0.key() not in MOVEMENT:
			return
		self.step(MOVEMENT[util.cast(a0.key())])

	def mouse_press(self, event):
		self.mouse_pos = event.pos()

	def mouse_release(self, event):
		if self.timer.isActive():
			return
		if self.my_thread:
			return
		if not self.mouse_pos:
			return

		delta_x = event.pos().x() - self.mouse_pos.x()
		delta_y = event.pos().y() - self.mouse_pos.y()
		self.mouse_pos = None

		if abs(delta_x) >= abs(delta_y):
			movement = "R" if delta_x >= 0 else "L"
		else:
			movement = "D" if delta_y >= 0 else "U"
		self.step(movement)

	def hinting(self):
		if self.timer.isActive():
			return
		if self.my_thread:
			return
		self.step(Algorithm.infer(self.board))

	def botting(self):
		if self.my_thread:
			self.toolButton_botting.setIcon(util.icon("../game2048/brain"))
			self.toolButton_botting.setToolTip("AI托管")
			self.my_thread.terminate()
			self.my_thread = None
		else:
			self.toolButton_botting.setIcon(util.icon("../game2048/terminate"))
			self.toolButton_botting.setToolTip("取消AI托管")
			self.my_thread = MyThread()
			self.my_thread.start()

	def display(self):
		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(FONT)
			for groove, pos in GROOVE.items():
				self.dye(painter, self.board[groove], pos)
		self.label.setPixmap(pixmap)

	def draw(self):
		self.timer.setProperty("frame", self.timer.property("frame") + 1)
		if self.timer.property("frame") > 10:
			self.timer.stop()
			return self.display()

		offset = self.timer.property("frame") / 10
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
		rect = QRect(*pos, 100, 100)
		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(COLOR[tile])
		painter.drawRect(rect)
		painter.setPen(COLOR["tile"])
		painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(tile).strip("0"))


class MyQ:
	@staticmethod
	def moving(board, movement):
		previous = board.copy()
		rotate = ROTATE[movement]
		trans = TRANS[movement]

		board = np.rot90(board, rotate)
		board, trails = MyQ.merge(board, trans)
		board = np.rot90(board, -rotate)

		if 2048 not in board and board.tolist() != previous.tolist():
			board = MyQ.add(board)
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
	def add(board):
		empty_cells = np.argwhere(board == 0)
		board[tuple(random.choice(empty_cells))] = 2 if random.random() < 0.9 else 4
		return board

	@staticmethod
	def win(board):
		return 2048 in board

	@staticmethod
	def lose(board):
		return 0 not in board and not any(0 in np.diff(f) for f in np.concatenate((board, board.T)))


class MyThread(QThread):
	signal_update = pyqtSignal()
	running = True

	def __init__(self):
		super().__init__()
		util.cast(self.signal_update).connect(self.update)

	def run(self):
		while self.running and not MyQ.win(my_core.board) and not MyQ.lose(my_core.board):
			util.cast(self.signal_update).emit()
			self.msleep(400)

	@staticmethod
	def update():
		my_core.step(Algorithm.infer(my_core.board))

	def terminate(self):
		self.running = False
		self.wait()


class Algorithm:
	@staticmethod
	def evaluate(board):
		empty_tiles = np.sum(board == 0)

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

		smoothness = 0

		#print("A", empty_count, max_tile, corner_priority, monotonicity, merge_potential)
		#print("B", empty_count * 2, math.log2(max_tile) * 5, corner_priority * 5, monotonicity, merge_potential)
		return empty_tiles * 3 + math.log2(max_tile) + corner_priority * 5 + monotonicity * 2 + merge_potential

	@staticmethod
	def expectimax(board, depth):
		if not depth or MyQ.lose(board):
			return Algorithm.evaluate(board)

		if depth % 2:
			score = -np.inf
			for movement in ROTATE.keys():
				subsequent, _ = MyQ.moving(board, movement)
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
			subsequent, _ = MyQ.moving(board, movement)
			if board.tolist() != subsequent.tolist():
				score = Algorithm.expectimax(subsequent, 3)
				if score > best_score:
					best_score = score
					best_movement = movement
		return best_movement


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
