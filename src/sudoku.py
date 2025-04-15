from sudoku_ui import Ui_MainWindow
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QMainWindow
from collections import defaultdict
from itertools import product
import numpy as np
import os
import sys
import util

PATH = {"graph": util.join_path(util.RESOURCE, "sudoku", "cache_graph.bin")}
CACHE = {"graph": np.fromfile(PATH["graph"], dtype=np.uint8).reshape(729, 324) if os.path.exists(PATH["graph"]) else None}


class MyCore(QMainWindow, Ui_MainWindow):
	SIZE = {"block": 60, "gap": 5}
	OFFSET = np.array((1, 1, -2, -2)) * SIZE["gap"]
	KEY = {
		"tile": {getattr(Qt.Key, f"Key_{i}"): i for i in range(1, 10)},
		"direction": {Qt.Key.Key_Up: (-1, 0), Qt.Key.Key_Down: (1, 0), Qt.Key.Key_Left: (0, -1), Qt.Key.Key_Right: (0, 1)}
	}

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../sudoku/logo"))

		self.skeleton = util.pixmap(image=("sudoku", "background.png"))
		self.label.setPixmap(self.skeleton.copy())
		self.label.mousePressEvent = self.mouse_press
		self.label.wheelEvent = self.wheel_scroll

		self.board = np.zeros((9, 9), dtype=np.int8)
		self.selection = self.previous = np.array((0, 0))
		self.__select()

	def mouse_press(self, event):
		pos = np.array((event.pos().y(), event.pos().x())) // self.SIZE["block"]
		self.previous = self.selection.copy()
		self.selection = np.clip(pos, 0, 8)
		self.__select()

	def wheel_scroll(self, event):
		self.board[tuple(self.selection)] += 1 if event.angleDelta().y() > 0 else -1
		self.board[tuple(self.selection)] = np.clip(self.board[tuple(self.selection)], 0, 9)
		self.__display()

	def keyPressEvent(self, event):
		if event.key() == Qt.Key.Key_Return:
			result = DancingLinksAlgorithm.solve(self.board)
			if isinstance(result, str):
				util.dialog(result, "error")
			else:
				self.__display(result=result)
			return

		if event.key() in self.KEY["tile"]:
			self.board[tuple(self.selection)] = self.KEY["tile"][event.key()]
		elif event.key() == Qt.Key.Key_Backspace:
			self.board[tuple(self.selection)] = 0
		elif event.key() in self.KEY["direction"]:
			self.previous = self.selection.copy()
			self.selection = np.clip(self.selection + self.KEY["direction"][event.key()], 0, 8)
		elif event.key() == Qt.Key.Key_Delete:
			self.board.fill(0)
			self.label.setPixmap(self.skeleton.copy())
		else:
			return
		self.__display()

	def __select(self):
		pixmap = self.label.pixmap()
		with QPainter(pixmap) as painter:
			self.__rect(painter, self.previous, QColor(243, 243, 243))
			self.__rect(painter, self.selection, QColor(200, 0, 0))
		self.label.setPixmap(pixmap)

	def __display(self, result=None):
		pixmap = self.label.pixmap()
		with QPainter(pixmap) as painter:
			painter.setFont(QFont("Arial", 24, QFont.Weight.Black))
			painter.setPen(Qt.GlobalColor.transparent)
			if result is None:
				rect = np.array((*self.selection[::-1], 1, 1)) * self.SIZE["block"] + self.OFFSET * 2
				painter.setBrush(QColor(243, 243, 243))
				painter.drawRect(QRect(*rect))
				painter.setBrush(Qt.GlobalColor.transparent)
				self.__rect(painter, self.selection, Qt.GlobalColor.black, board=self.board)
			else:
				for pos in np.argwhere(self.board != 0):
					self.__rect(painter, pos, Qt.GlobalColor.black, board=self.board)
				for pos in np.argwhere(self.board == 0):
					self.__rect(painter, pos, Qt.GlobalColor.gray, board=result)
		self.label.setPixmap(pixmap)
		self.__select()

	def __rect(self, painter, pos, color, board=None):
		painter.setPen(QPen(color, 2))
		rect = np.array((*pos[::-1], 1, 1)) * self.SIZE["block"]
		if board is None:
			painter.drawRect(QRect(*(rect + self.OFFSET)))
		else:
			painter.drawText(QRect(*rect), Qt.AlignmentFlag.AlignCenter, str(board[tuple(pos)]).strip("0"))


class DancingLinksAlgorithm:
	class Node:
		__slots__ = ["r", "c", "up", "down", "left", "right"]

		def __init__(self, r, c):
			self.r, self.c = r, c
			self.up = self.down = self.left = self.right = self

	@staticmethod
	def to_graph(board):
		graph = CACHE["graph"].copy()
		for (i, j) in np.argwhere(board != -1):
			r, k = i * 81 + j * 9, board[i, j]
			graph[r:r + k, :].fill(0)
			graph[r + k + 1:r + 9, :].fill(0)
		return graph

	@staticmethod
	def to_links(graph):
		links = tuple(DancingLinksAlgorithm.Node(-1, c) for c in range(graph.shape[1]))
		counts = defaultdict(int)
		for c, link in enumerate(links):
			link.left, link.right = links[c - 1], links[c + 1 - len(links)]
			link.left.right = link.right.left = link
		for r in range(graph.shape[0]):
			nodes = tuple(DancingLinksAlgorithm.Node(r, c) for c in np.where(graph[r] == 1)[0])
			for i, node in enumerate(nodes):
				counts[node.c] += 1
				node.up, node.down = links[node.c].up, links[node.c]
				node.up.down = node.down.up = node
				node.left, node.right = nodes[i - 1], nodes[i + 1 - len(nodes)]
				node.left.right = node.right.left = node
		return links, counts

	@staticmethod
	def to_head(links):
		head = DancingLinksAlgorithm.Node(-1, -1)
		head.left, head.right = links[-1], links[0]
		head.left.right = head.right.left = head
		return head

	@staticmethod
	def to_board(ans):
		ans = np.array(ans)
		board = np.zeros((9, 9), dtype=np.int8)
		board[ans // 81, ans // 9 % 9] = ans % 9
		return board

	@staticmethod
	def cover(link, counts):
		node = link.down
		while node != link:
			n = node.right
			while n != node:
				counts[n.c] -= 1
				n.up.down, n.down.up = n.down, n.up
				n = n.right
			node = node.down
		link.left.right, link.right.left = link.right, link.left

	@staticmethod
	def uncover(link, counts):
		node = link.down
		while node != link:
			n = node.right
			while n != node:
				counts[n.c] += 1
				n.up.down = n.down.up = n
				n = n.right
			node = node.down
		link.left.right = link.right.left = link

	@staticmethod
	def search(links, head, counts, ans):
		if head.right == head:
			return True

		link, count = None, np.inf
		node = head.right
		while node != head:
			if 0 <= counts[node.c] < count:
				link, count = node, counts[node.c]
			node = node.right
		if not link:
			return False

		DancingLinksAlgorithm.cover(link, counts)
		node = link.down
		while node != link:
			ans.append(node.r)
			n = node.right
			while n != node:
				DancingLinksAlgorithm.cover(links[n.c], counts)
				n = n.right

			if DancingLinksAlgorithm.search(links, head, counts, ans):
				return True

			ans.pop()
			n = node.left
			while n != node:
				DancingLinksAlgorithm.uncover(links[n.c], counts)
				n = n.left

			node = node.down
		DancingLinksAlgorithm.uncover(link, counts)
		return False

	@staticmethod
	def solve(board):
		if np.count_nonzero(board != 0) < 17:
			return "已知数不可少于17个"
		for i, row in enumerate(board):
			if any(np.bincount(row)[1:] > 1):
				return f"第{i + 1}行中有重复项"
		for j, col in enumerate(board.T):
			if any(np.bincount(col)[1:] > 1):
				return f"第{j + 1}列中有重复项"
		for i, j in product(range(0, 9, 3), repeat=2):
			palace = np.array(board[i:i + 3, j:j + 3]).reshape(-1)
			if any(np.bincount(palace)[1:] > 1):
				return f"第{(i // 3) * 3 + j // 3 + 1}宫中有重复项"

		graph = DancingLinksAlgorithm.to_graph(board - 1)
		links, counts = DancingLinksAlgorithm.to_links(graph)
		head = DancingLinksAlgorithm.to_head(links)
		
		ans = []
		DancingLinksAlgorithm.search(links, head, counts, ans)
		return (DancingLinksAlgorithm.to_board(ans) + 1) if ans else "未求得对应解"


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
