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
import mylibrary.myutil as mu

PATH = {"graph": util.join_path(util.RESOURCE, "sudoku", "cache_graph.bin")}
CACHE = {"graph": np.fromfile(PATH["graph"], dtype=np.uint8).reshape(729, 324) if os.path.exists(PATH["graph"]) else None}


class MyCore(QMainWindow, Ui_MainWindow):
	KEY_NUM = {getattr(Qt.Key, f"Key_{i}"): i for i in range(1, 10)}
	KEY_DIR = {Qt.Key.Key_Up: (-1, 0), Qt.Key.Key_Down: (1, 0), Qt.Key.Key_Left: (0, -1), Qt.Key.Key_Right: (0, 1)}
	board, result, selection = np.zeros((9, 9), dtype=np.int8), np.zeros((9, 9), dtype=np.int8), None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../sudoku/logo"))
		MyDisplayer.draw(self.board, self.result, self.selection, self.label)

	def mousePressEvent(self, a0):
		x, y = (a0.pos().y() - 15) // 60, (a0.pos().x() - 15) // 60
		if 0 <= x <= 8 and 0 <= y <= 8:
			self.selection = None if (x, y) == self.selection else (x, y)
			MyDisplayer.draw(self.board, self.result, self.selection, self.label)

	def keyPressEvent(self, a0):
		if a0.key() in self.KEY_NUM and self.selection:
			self.board[self.selection] = self.KEY_NUM[a0.key()]
			MyDisplayer.draw(self.board, self.result, self.selection, self.label)
		elif a0.key() in self.KEY_DIR and self.selection:
			self.selection = (
				min(max(self.selection[0] + self.KEY_DIR[util.cast(a0.key())][0], 0), 8),
				min(max(self.selection[1] + self.KEY_DIR[util.cast(a0.key())][1], 0), 8)
			)
			MyDisplayer.draw(self.board, self.result, self.selection, self.label)
		elif a0.key() == Qt.Key.Key_Backspace and self.selection:
			self.board[self.selection] = 0
			self.result[self.selection] = 0
			MyDisplayer.draw(self.board, self.result, self.selection, self.label)
		elif a0.key() == Qt.Key.Key_Delete:
			self.selection = None
			self.board.fill(0)
			self.result.fill(0)
			MyDisplayer.draw(self.board, self.result, self.selection, self.label)
		elif a0.key() == Qt.Key.Key_Return:
			result = DancingLinksAlgorithm.solve(self.board)
			if isinstance(result, str):
				util.dialog(result, "error")
			else:
				self.selection = None
				self.result = result
				MyDisplayer.draw(self.board, self.result, self.selection, self.label)
				util.dialog("求解成功", "success")


class MyDisplayer:
	@staticmethod
	def draw(board, result, selection, label):
		pixmap = QPixmap(550, 550)
		pixmap.fill(Qt.GlobalColor.transparent)
		with QPainter(pixmap) as painter:
			painter.setFont(QFont(QFont().family(), 20, QFont.Weight.Bold))
			for i, j in product(range(9), repeat=2):
				rect = QRect(j * 60 + 5, i * 60 + 5, 60, 60)
				painter.setBrush(QColor(200, 230, 255) if (i, j) == selection else QColor(Qt.GlobalColor.transparent))
				painter.setPen(QPen(Qt.GlobalColor.gray, 1))
				painter.drawRect(rect)

				if board[i, j] != 0:
					painter.setPen(QPen(QColor(200, 0, 0), 1))
					painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(board[i, j]))
				elif result[i, j] != 0:
					painter.setPen(QPen(QColor(112, 169, 97), 1))
					painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(result[i, j]))
				else:
					painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "")

			painter.setBrush(Qt.GlobalColor.transparent)
			painter.setPen(QPen(Qt.GlobalColor.black, 2))
			for i, j in product(range(3), repeat=2):
				painter.drawRect(QRect(j * 180 + 5, i * 180 + 5, 180, 180))
		label.setPixmap(pixmap)


class DancingLinksAlgorithm:
	class Node:
		__slots__ = ["r", "c", "up", "down", "left", "right"]

		def __init__(self, r, c):
			self.r, self.c = r, c
			self.up = self.down = self.left = self.right = self

	@staticmethod
	def to_graph(board):
		graph = CACHE["graph"].copy()
		for (i, j), k in product(np.argwhere(board != -1), range(9)):
			graph[i * 81 + j * 9 + k] *= (k == board[i, j])
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
	@mu.Decorator.timing
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
