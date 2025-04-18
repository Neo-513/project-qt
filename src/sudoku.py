from sudoku_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter
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
	SIZE = 60
	KEY = {getattr(Qt.Key, f"Key_{i + 1}"): i + 1 for i in range(9)}
	IMG = {
		"black": tuple(util.image(f"../sudoku/black{i}") for i in range(9)),
		"gray": tuple(util.image(f"../sudoku/gray{i}") for i in range(9)),
		"selection": util.image(f"../sudoku/selection")
	}

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../sudoku/logo"))

		self.label_background = util.mask(self.label_canvas.minimumSize(), (9, 9), self.centralwidget)
		self.label_background.setPixmap(util.pixmap("../sudoku/background"))
		self.label_cover = util.mask(self.label_canvas.minimumSize(), (9, 9), self.centralwidget, pointer=True)
		self.label_cover.mousePressEvent = self.press_mouse
		util.pixmap(self.label_cover, color=Qt.GlobalColor.transparent)
		util.pixmap(self.label_canvas, color=Qt.GlobalColor.transparent)

		self.board = np.zeros((9, 9), dtype=np.int8)
		self.selection = 0, 0
		self.select()

	def press_mouse(self, event):
		pos = event.pos().y() // self.SIZE, event.pos().x() // self.SIZE
		self.selection = tuple(np.clip(pos, 0, 8))
		self.select()

	def wheelEvent(self, event):
		self.board[self.selection] += 1 if event.angleDelta().y() > 0 else -1
		self.board[self.selection] = np.clip(self.board[self.selection], 0, 9)
		self.display(self.selection, "black", self.board[self.selection])

	def keyPressEvent(self, event):
		if event.key() in self.KEY:
			self.board[self.selection] = self.KEY[event.key()]
			self.display(self.selection, "black", self.board[self.selection])
			return
		if event.key() == Qt.Key.Key_Backspace:
			self.board[self.selection] = 0
			self.display(self.selection, "black", self.board[self.selection])
			return
		if event.key() == Qt.Key.Key_Delete:
			self.board.fill(0)
			pixmap = self.label_canvas.pixmap()
			pixmap.fill(Qt.GlobalColor.transparent)
			self.label_canvas.setPixmap(pixmap)
			return
		if event.key() == Qt.Key.Key_Return:
			result = DancingLinksAlgorithm.solve(self.board)
			if isinstance(result, str):
				util.dialog(result, "error")
			else:
				for pos in np.argwhere(self.board != 0):
					self.display(pos, "black", self.board[tuple(pos)])
				for pos in np.argwhere(self.board == 0):
					self.display(pos, "gray", result[tuple(pos)])
			return

	def display(self, pos, color, tile):
		xy = pos[1] * self.SIZE, pos[0] * self.SIZE
		zw = self.SIZE, self.SIZE

		pixmap = self.label_canvas.pixmap()
		with QPainter(pixmap) as painter:
			painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
			painter.fillRect(*xy, *zw, Qt.GlobalColor.transparent)
			if tile != 0:
				painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
				painter.drawImage(*xy, self.IMG[color][tile - 1])
		self.label_canvas.setPixmap(pixmap)

	def select(self):
		pixmap = self.label_cover.pixmap()
		pixmap.fill(Qt.GlobalColor.transparent)
		with QPainter(pixmap) as painter:
			painter.drawImage(self.selection[1] * self.SIZE, self.selection[0] * self.SIZE, self.IMG["selection"])
		self.label_cover.setPixmap(pixmap)


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
			return f"已知数{np.count_nonzero(board != 0)}个不可少于17个"
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
