from game2048_ui import Ui_MainWindow
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from functools import lru_cache
from itertools import product
import numpy as np
import os
import random
import sys
import util

PATH = {
	"sequential": util.join_path(util.RESOURCE, "game2048", "cache_sequential.pkl"),
	"reversed": util.join_path(util.RESOURCE, "game2048", "cache_reversed.pkl"),
	"mono": util.join_path(util.RESOURCE, "game2048", "cache_mono.pkl"),
	"smooth": util.join_path(util.RESOURCE, "game2048", "cache_smooth.pkl"),
	"merge": util.join_path(util.RESOURCE, "game2048", "cache_merge.pkl")
}
CACHE = {
	"sequential": util.read(PATH["sequential"]) if os.path.exists(PATH["sequential"]) else None,
	"reversed": util.read(PATH["reversed"]) if os.path.exists(PATH["reversed"]) else None,
	"mono": util.read(PATH["mono"]) if os.path.exists(PATH["mono"]) else None,
	"smooth": util.read(PATH["smooth"]) if os.path.exists(PATH["smooth"]) else None,
	"merge": util.read(PATH["merge"]) if os.path.exists(PATH["merge"]) else None
}


class MyCore(QMainWindow, Ui_MainWindow):
	WEIGHT = (0.605904, 0.900348, 0.196291, 0.508765, 0.909638)
	KEY = {Qt.Key.Key_Left: "L", Qt.Key.Key_Right: "R", Qt.Key.Key_Up: "U", Qt.Key.Key_Down: "D"}

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../game2048/logo"))

		util.button(self.pushButton, self.restart, tip="新游戏")
		util.button(self.toolButton_hinting, self.hinting, "../game2048/hint", tip="提示", ico_size=32)
		util.button(self.toolButton_botting, self.botting, "../game2048/nonbotting", tip="托管", ico_size=32)
		self.label.mousePressEvent = self.mouse_press
		self.label.mouseReleaseEvent = self.mouse_release

		self.board = np.zeros((4, 4), dtype=np.int8)
		self.skeleton = MyDisplayer.skeletonize()
		self.mouse_pos = None
		self.timer1 = util.timer(15, self.timeout1)
		self.timer2 = util.timer(160, self.timeout2)
		self.restart()

	def restart(self):
		if self.timer1.isActive():
			self.timer1.stop()
		if self.timer2.isActive():
			self.timer2.stop()
		self.toolButton_botting.setIcon(util.icon("../game2048/nonbotting"))
		self.toolButton_hinting.setIcon(util.icon("../game2048/hint"))
		self.board.fill(0)
		MyMatrixer.add(self.board)
		MyMatrixer.add(self.board)
		MyDisplayer.display(self)

	def keyPressEvent(self, event):
		if self.timer1.isActive() or self.timer2.isActive():
			return
		if event.key() in MyCore.KEY:
			self.act(MyCore.KEY[event.key()])

	def mouse_press(self, event):
		self.mouse_pos = event.pos()

	def mouse_release(self, event):
		if self.timer1.isActive() or self.timer2.isActive():
			return
		if not self.mouse_pos:
			return

		dx = event.pos().x() - self.mouse_pos.x()
		dy = event.pos().y() - self.mouse_pos.y()
		self.mouse_pos = None

		if abs(dx) >= abs(dy):
			movement = "R" if dx >= 0 else "L"
		else:
			movement = "D" if dy >= 0 else "U"
		self.act(movement)

	def hinting(self):
		if self.timer1.isActive() or self.timer2.isActive():
			return
		self.act(ExpectimaxAlgorithm.solve(self.board, MyCore.WEIGHT))

	def botting(self):
		if self.timer2.isActive():
			self.timer2.stop()
			self.toolButton_botting.setIcon(util.icon("../game2048/nonbotting"))
			self.toolButton_hinting.setIcon(util.icon("../game2048/hint"))
			MyDisplayer.display(self)
		else:
			self.toolButton_botting.setIcon(util.icon("../game2048/botting"))
			self.toolButton_hinting.setIcon(util.icon("../game2048/nonhint"))
			self.timer2.start()

	def timeout1(self):
		self.timer1.frame += 1
		if self.timer1.frame > 10:
			self.timer1.stop()
			MyDisplayer.display(self)
			return

		offset = self.timer1.frame / 10
		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(MyDisplayer.FONT)
			for (sx, sy), (ex, ey), tile in self.timer1.trails:
				groove = int(sx + (ex - sx) * offset), int(sy + (ey - sy) * offset)
				MyDisplayer.draw(painter, tile, groove)
		self.label.setPixmap(pixmap)

	def timeout2(self):
		if MyMatrixer.win(self.board) or MyMatrixer.lose(self.board):
			return
		self.act(ExpectimaxAlgorithm.solve(self.board, MyCore.WEIGHT))

	def act(self, movement):
		previous = self.board.copy()
		self.board = MyMatrixer.move(self.board, movement)

		self.timer1.frame = 0
		self.timer1.trails = MyDisplayer.track(previous.copy(), self.board.copy(), movement)
		self.timer1.start()

		if MyMatrixer.win(self.board):
			self.toolButton_botting.setIcon(util.icon("../game2048/nonbotting"))
			self.toolButton_hinting.setIcon(util.icon("../game2048/hint"))
			util.dialog("You win", "success")
			return self.restart()
		if not np.array_equal(self.board, previous):
			MyMatrixer.add(self.board)
		if MyMatrixer.lose(self.board):
			self.toolButton_botting.setIcon(util.icon("../game2048/nonbotting"))
			self.toolButton_hinting.setIcon(util.icon("../game2048/hint"))
			util.dialog("You lose", "error")
			return self.restart()


class MyDisplayer:
	GROOVE = {(i, j): (j * 115 + 15, i * 115 + 15) for i, j in product(range(4), repeat=2)}
	FONT = QFont(QFont().family(), 40, QFont.Weight.Bold)
	COLOR = [
		(205, 193, 180), (238, 228, 218), (237, 224, 200), (242, 177, 121), (245, 149, 99), (246, 124, 95),
		(246, 94, 59), (237, 207, 114), (237, 204, 97), (228, 192, 42), (226, 186, 19), (236, 196, 0)
	]
	TRANS = {
		"L": lambda x, y: MyDisplayer.GROOVE[x, y], "R": lambda x, y: MyDisplayer.GROOVE[3 - x, 3 - y],
		"U": lambda x, y: MyDisplayer.GROOVE[y, 3 - x], "D": lambda x, y: MyDisplayer.GROOVE[3 - y, x]
	}

	@staticmethod
	def skeletonize():
		pixmap = QPixmap(475, 475)
		pixmap.fill(QColor(187, 173, 160))
		with QPainter(pixmap) as painter:
			for groove in MyDisplayer.GROOVE.values():
				MyDisplayer.draw(painter, 0, groove)
		return pixmap

	@staticmethod
	def display(self):
		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(MyDisplayer.FONT)
			for pos, groove in MyDisplayer.GROOVE.items():
				MyDisplayer.draw(painter, self.board[pos], groove)
		self.label.setPixmap(pixmap)

	@staticmethod
	def draw(painter, tile, groove):
		rect = QRect(*groove, 100, 100)
		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(QColor(*MyDisplayer.COLOR[tile]))
		painter.drawRect(rect)
		painter.setPen(QColor(118, 110, 101))
		painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(2 ** tile).rstrip("1"))

	@staticmethod
	def track(previous, subsequent, movement):
		trans = MyDisplayer.TRANS[movement]
		if movement == "R":
			previous = previous[::-1, ::-1]
			subsequent = subsequent[::-1, ::-1]
		if movement == "U":
			previous = previous.T[::-1]
			subsequent = subsequent.T[::-1]
		if movement == "D":
			previous = previous[::-1].T
			subsequent = subsequent[::-1].T

		trails = []
		for i in range(4):
			k = 0
			for j in range(4):
				if previous[i, j] == 0:
					continue
				trails.append((trans(i, j), trans(i, k), previous[i, j]))
				if subsequent[i, k] == previous[i, j]:
					k += 1
				else:
					subsequent[i, k] -= 1
		return trails[::-1]


class MyMatrixer:
	@staticmethod
	def move(board, movement):
		board = board.T if movement in "UD" else board
		for i in range(4):
			board[i] = CACHE["sequential" if movement in "LU" else "reversed"][board[i].tobytes()]
		return board.T if movement in "UD" else board

	@staticmethod
	def add(board):
		board[tuple(random.choice(np.argwhere(board == 0)))] = 1 if random.random() <= 0.9 else 2

	@staticmethod
	def win(board):
		return 11 in board

	@staticmethod
	def lose(board):
		return (0 not in board) and (0 not in np.diff(board)) and (0 not in np.diff(board.T))


class ExpectimaxAlgorithm:
	@staticmethod
	def solve(board, weight):
		max_depth = 3 if np.max(board) >= 8 else 2
		movement, _ = ExpectimaxAlgorithm.search(board, weight, 0, max_depth)
		return movement

	@staticmethod
	def search(board, weight, depth, max_depth):
		if max_depth == 3:
			return ExpectimaxAlgorithm.__search_cache(board.tobytes(), weight, depth, max_depth)
		else:
			return ExpectimaxAlgorithm.__search_nocache(board, weight, depth, max_depth)

	@staticmethod
	@lru_cache(maxsize=100000)
	def __search_cache(board, weight, depth, max_depth):
		board = np.frombuffer(board, dtype=np.int8).reshape((4, 4))
		return ExpectimaxAlgorithm.__search_nocache(board, weight, depth, max_depth)

	@staticmethod
	def __search_nocache(board, weight, depth, max_depth):
		if MyMatrixer.win(board):
			return None, 10000
		if MyMatrixer.lose(board):
			return None, -10000
		if depth >= max_depth:
			return None, ExpectimaxAlgorithm.evaluate(board, weight)

		if depth % 2 == 0:
			best_movement, best_score = None, -np.inf
			for movement in "LRUD":
				subsequent = MyMatrixer.move(board.copy(), movement)
				if not np.array_equal(board, subsequent):
					_, score = ExpectimaxAlgorithm.search(subsequent, weight, depth + 1, max_depth)
					if score > best_score:
						best_movement, best_score = movement, score
			return best_movement, best_score
		else:
			if 0 not in board:
				return None, ExpectimaxAlgorithm.evaluate(board, weight)
			empty_cells = np.argwhere(board == 0)
			probs, best_score = {2: 0.9 / len(empty_cells), 4: 0.1 / len(empty_cells)}, 0
			for empty_cell, (tile, prob) in product(empty_cells, probs.items()):
				subsequent = board.copy()
				subsequent[tuple(empty_cell)] = tile
				_, score = ExpectimaxAlgorithm.search(subsequent, weight, depth + 1, max_depth)
				best_score += prob * score
			return None, best_score

	@staticmethod
	def evaluate(board, weight):
		mono = smooth = merge = 0
		for b in board:
			byt = b.tobytes()
			mono += CACHE["mono"][byt]
			smooth -= CACHE["smooth"][byt]
			merge += CACHE["merge"][byt]
		for b in board.T:
			byt = b.tobytes()
			mono += CACHE["mono"][byt]
			smooth -= CACHE["smooth"][byt]
			merge += CACHE["merge"][byt]
		return (
			weight[0] * (np.max(board) in (board[0, 0], board[0, 3], board[3, 0], board[3, 3])) * 15 +
			weight[1] * np.sum(board == 0) + weight[2] * mono + weight[3] * smooth + weight[4] * merge
		)


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
