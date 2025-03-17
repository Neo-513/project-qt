from sudoku_ui import Ui_MainWindow
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
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
	KEY = {
		"tile": {getattr(Qt.Key, f"Key_{i}"): i for i in range(1, 10)},
		"direction": {Qt.Key.Key_Up: (-1, 0), Qt.Key.Key_Down: (1, 0), Qt.Key.Key_Left: (0, -1), Qt.Key.Key_Right: (0, 1)}
	}

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../sudoku/logo"))

		self.label.mousePressEvent = self.mouse_press
		self.label.wheelEvent = self.wheel_scroll

		self.board = np.zeros((9, 9), dtype=int)
		self.result = np.zeros((9, 9), dtype=int)
		self.selection = (0, 0)
		self.skeleton = MyDisplayer.skeletonize()
		MyDisplayer.display(self)

	def mouse_press(self, event):
		x, y = (event.pos().y() - 5) // 60, (event.pos().x() - 5) // 60
		if 0 <= x <= 8 and 0 <= y <= 8:
			self.selection = x, y
			MyDisplayer.display(self)

	def wheel_scroll(self, event):
		self.board[self.selection] += 1 if event.angleDelta().y() > 0 else -1
		self.board[self.selection] = np.clip(int(self.board[self.selection]), 0, 9)
		self.result[self.selection] = 0
		MyDisplayer.display(self)

	def keyPressEvent(self, event):
		if event.key() in self.KEY["tile"]:
			self.board[self.selection] = self.KEY["tile"][event.key()]
		elif event.key() in self.KEY["direction"]:
			offset = self.KEY["direction"][util.cast(event.key())]
			self.selection = (
				np.clip(self.selection[0] + offset[0], 0, 8),
				np.clip(self.selection[1] + offset[1], 0, 8)
			)
		elif event.key() == Qt.Key.Key_Backspace:
			self.board[self.selection] = 0
			self.result[self.selection] = 0
		elif event.key() == Qt.Key.Key_Delete:
			self.board.fill(0)
			self.result.fill(0)
		elif event.key() == Qt.Key.Key_Return:
			result = DancingLinksAlgorithm.solve(self.board)
			if isinstance(result, str):
				util.dialog(result, "error")
			else:
				self.result = result
				util.dialog("求解成功", "success")
		else:
			return
		MyDisplayer.display(self)


class MyRect:
	SIZE = {"block": 60, "margin": 5, "padding": 10}

	@staticmethod
	def to_rect(i, j, rect_type):
		block, margin, padding = MyRect.SIZE["block"], MyRect.SIZE["margin"], MyRect.SIZE["padding"]
		if rect_type == "block":
			return j * block + margin, i * block + margin, block, block
		if rect_type == "palace":
			block *= 3
			return j * block + margin, i * block + margin, block, block
		if rect_type == "selection":
			return j * block + padding, i * block + padding, block - padding, block - padding


class MyDisplayer:
	RECT = {
		"block": {(i, j): MyRect.to_rect(i, j, "block") for i, j in product(range(9), repeat=2)},
		"palace": tuple(MyRect.to_rect(i, j, "palace") for i, j in product(range(3), repeat=2)),
		"selection": {(i, j): MyRect.to_rect(i, j, "selection") for i, j in product(range(9), repeat=2)}
	}

	@staticmethod
	def skeletonize():
		size = MyRect.SIZE["block"] * 9 + MyRect.SIZE["margin"] * 2
		pixmap = QPixmap(size, size)
		pixmap.fill(Qt.GlobalColor.transparent)
		with QPainter(pixmap) as painter:
			painter.setBrush(QColor(Qt.GlobalColor.transparent))
			painter.setPen(QPen(Qt.GlobalColor.gray, 1))
			for block in MyDisplayer.RECT["block"].values():
				painter.drawRect(QRect(*block))
			painter.setPen(QPen(Qt.GlobalColor.black, 2))
			for palace in MyDisplayer.RECT["palace"]:
				painter.drawRect(QRect(*palace))
		return pixmap

	@staticmethod
	def display(self):
		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(QFont("Arial", 24, QFont.Weight.Black))
			painter.setBrush(Qt.GlobalColor.transparent)
			for pos, block in MyDisplayer.RECT["block"].items():
				painter.setPen(Qt.GlobalColor.black if self.board[pos] else Qt.GlobalColor.gray)
				painter.drawText(QRect(*block), Qt.AlignmentFlag.AlignCenter, str(self.board[pos] or self.result[pos] or ""))
			painter.setPen(QPen(QColor(200, 0, 0), 2))
			painter.drawRect(QRect(*MyDisplayer.RECT["selection"][self.selection]))
		self.label.setPixmap(pixmap)


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
		board = np.zeros((9, 9), dtype=int)
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
			palace = np.array(board[i:i + 3, j:j + 3]).flatten()
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
