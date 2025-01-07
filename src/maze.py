from maze_ui import Ui_MainWindow
from PyQt6.QtCore import pyqtSignal, QRectF, QThread, Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import product
import random
import sys
import util

WALL, ROUTE = 0, 1
DIRECTION = {Qt.Key.Key_Up: (-1, 0), Qt.Key.Key_Down: (1, 0), Qt.Key.Key_Left: (0, -1), Qt.Key.Key_Right: (0, 1)}


class MyCore(QMainWindow, Ui_MainWindow):
	my_thread = None
	row_count, column_count, block_size = None, None, None
	field, puppet, target = None, None, None
	skeleton, nerve, route = [], [], []
	searched, enlightened = [], []

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../maze/robot"))

		util.button(self.pushButton_generate, self.generate, "../maze/maze")
		util.button(self.pushButton_search, self.search, "../maze/locate")
		util.button(self.toolButton_clear, self.clear, "delete")
		util.button(self.toolButton_replay, self.replay, "../maze/replay")
		util.button(self.toolButton_row_min, lambda: self.spinBox_row.setValue(self.spinBox_row.minimum()), "../maze/min")
		util.button(self.toolButton_row_max, lambda: self.spinBox_row.setValue(self.spinBox_row.maximum()), "../maze/max")
		util.button(self.toolButton_column_min, lambda: self.spinBox_column.setValue(self.spinBox_column.minimum()), "../maze/min")
		util.button(self.toolButton_column_max, lambda: self.spinBox_column.setValue(self.spinBox_column.maximum()), "../maze/max")

		self.generate()

	def generate(self):
		row, column = self.spinBox_row.value(), self.spinBox_column.value()
		self.row_count, self.column_count = row * 2 + 1, column * 2 + 1

		w, h = self.frame.minimumWidth(), self.frame.minimumHeight()
		self.block_size = round(min(w / self.column_count, h / self.row_count), 4)

		self.label_canvas.setFixedSize(int(self.column_count * self.block_size), int(self.row_count * self.block_size))
		pixmap = QPixmap(self.label_canvas.width(), self.label_canvas.height())
		pixmap.fill(Qt.GlobalColor.black)
		self.label_canvas.setPixmap(pixmap)

		algorithm = self.comboBox_generate.currentText()
		if algorithm == "随机DFS":
			MyGenerator.randomized_dfs(self)
		MyStatic.rebuild(self)

		self.route = [(i, j) for i, j in product(range(self.row_count), range(self.column_count)) if self.field[i][j]]
		self.puppet, self.target = random.sample(self.route, 2)
		self.clear()

	def search(self, replay=False):
		algorithm = self.comboBox_search.currentText()
		if algorithm == "深度优先(DFS)":
			MySearcher.dfs()
		elif algorithm == "广度优先(BFS)":
			MySearcher.bfs()

		self.searched.remove(self.puppet) if self.puppet in self.searched else None
		self.enlightened.remove(self.puppet) if self.puppet in self.enlightened else None
		self.searched.remove(self.target) if self.target in self.searched else None
		self.enlightened.remove(self.target) if self.target in self.enlightened else None

		self.clear()
		if not replay:
			self.draw(self.searched, Qt.GlobalColor.darkGreen)
			self.draw(self.enlightened, Qt.GlobalColor.green)

		self.progressBar_searched.setMaximum(len(self.searched))
		self.progressBar_searched.setValue(self.progressBar_searched.maximum())

		self.progressBar_enlightened.setMaximum(len(self.enlightened))
		self.progressBar_enlightened.setValue(self.progressBar_enlightened.maximum())

	def clear(self):
		self.draw(self.route)
		self.progressBar_searched.setValue(0)
		self.progressBar_enlightened.setValue(0)
	
	def replay(self):
		if abs(self.puppet[0] - self.target[0]) + abs(self.puppet[1] - self.target[1]) == 1:
			return
		self.search(replay=True)
		self.my_thread = MyThread()
		self.my_thread.start()

	def draw(self, blocks, color=Qt.GlobalColor.gray, highlight=True):
		pixmap = self.label_canvas.pixmap()
		painter = QPainter(pixmap)
		painter.setPen(Qt.PenStyle.NoPen)

		painter.setBrush(color)
		for block in blocks:
			MyStatic.draw_block(self, block, painter)

		if highlight:
			painter.setBrush(Qt.GlobalColor.red)
			MyStatic.draw_block(self, self.target, painter)
			painter.setBrush(Qt.GlobalColor.blue)
			MyStatic.draw_block(self, self.puppet, painter)

		painter.end()
		self.label_canvas.setPixmap(pixmap)

	def keyPressEvent(self, a0):
		if a0.key() in DIRECTION:
			direction = DIRECTION[util.cast(a0.key())]
			pos = self.puppet[0] + direction[0], self.puppet[1] + direction[1]
			if self.field[pos[0]][pos[1]]:
				self.puppet, pos = pos, self.puppet
				self.draw([pos])
			if self.puppet == self.target:
				util.dialog("You won", "success")
				return self.generate()


class MyGenerator:
	@staticmethod
	def randomized_dfs(self):
		visited = [[False] * self.spinBox_column.value() for _ in range(self.spinBox_row.value())]
		self.skeleton.clear()
		MyGenerator._randomized_dfs(self, 0, 0, visited)

	@staticmethod
	def _randomized_dfs(self, x, y, visited):
		visited[x][y] = True
		directions = list(DIRECTION.values())
		random.shuffle(directions)

		for i, j in directions:
			if not 0 <= x + i < self.spinBox_row.value():
				continue
			if not 0 <= y + j < self.spinBox_column.value():
				continue
			if visited[x + i][y + j]:
				continue
			self.skeleton.append(((x, y), (x + i, y + j)))
			MyGenerator._randomized_dfs(self, x + i, y + j, visited)


class MySearcher:
	@staticmethod
	def dfs():
		visited = [[False] * my_core.column_count for _ in range(my_core.row_count)]
		my_core.searched.clear()
		my_core.enlightened.clear()
		MySearcher._dfs(my_core.puppet[0], my_core.puppet[1], visited)

	@staticmethod
	def _dfs(x, y, visited):
		if (x, y) == my_core.target:
			return True
		visited[x][y] = True

		for i, j in DIRECTION.values():
			if not MyStatic.is_route(x + i, y + j):
				continue
			if visited[x + i][y + j]:
				continue
			my_core.searched.append((x + i, y + j))
			if MySearcher._dfs(x + i, y + j, visited):
				my_core.enlightened.append((x + i, y + j))
				return True

	@staticmethod
	def bfs():
		visited = [[False] * my_core.column_count for _ in range(my_core.row_count)]
		queue = [my_core.puppet]
		branch = {}
		my_core.searched.clear()
		my_core.enlightened.clear()

		while queue:
			x, y = queue.pop(0)
			if (x, y) == my_core.target:
				break
			visited[x][y] = True

			my_core.searched.append((x, y))
			for i, j in DIRECTION.values():
				if not MyStatic.is_route(x + i, y + j):
					continue
				if visited[x + i][y + j]:
					continue
				branch[(x + i, y + j)] = (x, y)
				queue.append((x + i, y + j))

		leaf = my_core.target
		while leaf in branch:
			my_core.enlightened.append(leaf)
			leaf = branch[leaf]


class MyStatic:
	@staticmethod
	def rebuild(self):
		self.field = [[WALL] * (self.column_count - 2) for _ in range(self.row_count - 2)]
		for s in self.skeleton:
			(x1, y1), (x2, y2) = s
			self.field[x1 * 2][y1 * 2] = ROUTE
			self.field[x2 * 2][y2 * 2] = ROUTE
			self.field[x1 + x2][y1 + y2] = ROUTE

		for f in self.field:
			f.insert(0, WALL)
			f.append(WALL)
		self.field.insert(0, [WALL] * self.column_count)
		self.field.append([WALL] * self.column_count)

	@staticmethod
	def draw_block(self, pos, painter):
		painter.drawRect(QRectF(pos[1] * self.block_size, pos[0] * self.block_size, self.block_size, self.block_size))

	@staticmethod
	def is_route(x, y):
		if not 0 <= x < my_core.row_count:
			return False
		if not 0 <= y < my_core.column_count:
			return False
		if not my_core.field[x][y]:
			return False
		return True


class MyThread(QThread):
	signal_starts = pyqtSignal()
	signal_update1 = pyqtSignal(tuple, int)
	signal_update2 = pyqtSignal(tuple, int)
	signal_finish = pyqtSignal()

	def __init__(self):
		super().__init__()
		util.cast(self.signal_starts).connect(self.starts)
		util.cast(self.signal_update1).connect(self.update1)
		util.cast(self.signal_update2).connect(self.update2)
		util.cast(self.signal_finish).connect(self.finish)

	def run(self):
		util.cast(self.signal_starts).emit()
		for i, e in enumerate(my_core.searched):
			util.cast(self.signal_update1).emit(e, i)
		for i, s in enumerate(my_core.enlightened):
			util.cast(self.signal_update2).emit(s, i)
		util.cast(self.signal_finish).emit()

	@staticmethod
	def starts():
		my_core.toolButton_replay.setEnabled(False)
		my_core.toolButton_replay.setIcon(util.icon("loading"))

		my_core.pushButton_generate.setEnabled(False)
		my_core.pushButton_search.setEnabled(False)
		my_core.toolButton_clear.setEnabled(False)

		my_core.progressBar_searched.setValue(0)
		my_core.progressBar_searched.setMaximum(len(my_core.searched))

		my_core.progressBar_enlightened.setValue(0)
		my_core.progressBar_enlightened.setMaximum(len(my_core.enlightened))

	def update1(self, block, value):
		my_core.draw([block], Qt.GlobalColor.darkGreen, highlight=False)
		my_core.progressBar_searched.setValue(value + 1)
		self.msleep(1)

	def update2(self, block, value):
		my_core.draw([block], Qt.GlobalColor.green, highlight=False)
		my_core.progressBar_enlightened.setValue(value + 1)
		self.msleep(1)

	@staticmethod
	def finish():
		my_core.toolButton_replay.setEnabled(True)
		my_core.toolButton_replay.setIcon(util.icon("../maze/replay"))

		my_core.pushButton_generate.setEnabled(True)
		my_core.pushButton_search.setEnabled(True)
		my_core.toolButton_clear.setEnabled(True)


if __name__ == "__main__":
	sys.setrecursionlimit(10000)
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
