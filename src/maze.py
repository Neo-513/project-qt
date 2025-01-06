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


class QtCore(QMainWindow, Ui_MainWindow):
	THREAD = None
	field, puppet, finish = None, None, None
	row_count, column_count, block_size = None, None, None
	barriers, routes = [], []
	explored, solution = [], []

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../maze/robot"))

		util.button(self.pushButton_maze, self.restart, "../maze/maze")
		util.button(self.pushButton_solve, self.solve, "../maze/locate")
		util.button(self.pushButton_replay, self.replay, "../maze/replay")
		util.button(self.pushButton_clear, self.clear, "delete")
		util.button(self.pushButton_min_row, lambda: self.spinBox_row.setValue(self.spinBox_row.minimum()), "../maze/min")
		util.button(self.pushButton_max_row, lambda: self.spinBox_row.setValue(self.spinBox_row.maximum()), "../maze/max")
		util.button(self.pushButton_min_column, lambda: self.spinBox_column.setValue(self.spinBox_column.minimum()), "../maze/min")
		util.button(self.pushButton_max_column, lambda: self.spinBox_column.setValue(self.spinBox_column.maximum()), "../maze/max")

		self.restart()

	def restart(self):
		row, column = self.spinBox_row.value(), self.spinBox_column.value()
		self.row_count, self.column_count = row * 2 + 1, column * 2 + 1

		w, h = self.frame.minimumWidth(), self.frame.minimumHeight()
		self.block_size = round(min(w / self.column_count, h / self.row_count), 4)

		self.label_canvas.setFixedSize(int(self.block_size * self.column_count), int(self.block_size * self.row_count))
		pixmap = QPixmap(self.label_canvas.width(), self.label_canvas.height())
		pixmap.fill(Qt.GlobalColor.black)
		self.label_canvas.setPixmap(pixmap)

		algorithm = self.comboBox_maze.currentText()
		if algorithm == "随机dfs":
			QtMaze.randomized_dfs(self)
		QtStatic.rebuild(self)

		self.routes = [(i, j) for i, j in product(range(self.row_count), range(self.column_count)) if self.field[i][j]]
		self.puppet, self.finish = random.sample(self.routes, 2)
		self.clear()

	def solve(self, replay=False):
		algorithm = self.comboBox_solve.currentText()
		if algorithm == "dfs":
			QtSolve.dfs(self)
		elif algorithm == "bfs":
			QtSolve.bfs(self)

		self.clear()
		self.draw(self.explored, Qt.GlobalColor.darkGreen) if not replay else None
		self.draw(self.solution, Qt.GlobalColor.green) if not replay else None

		self.spinBox_solution.setValue(len(self.solution) - 1)
		self.spinBox_explored.setValue(len(self.explored) - 1)

	def replay(self):
		self.solve(replay=True)
		self.THREAD = QtThread()
		self.THREAD.start()

	def clear(self):
		self.draw(self.routes)
		self.spinBox_solution.setValue(0)
		self.spinBox_explored.setValue(0)

	def draw(self, blocks, color=Qt.GlobalColor.gray):
		def _draw(pos):
			painter.drawRect(QRectF(pos[1] * self.block_size, pos[0] * self.block_size, self.block_size, self.block_size))

		if not blocks:
			return

		pixmap = self.label_canvas.pixmap()
		painter = QPainter(pixmap)
		painter.setPen(Qt.PenStyle.NoPen)

		for block in blocks:
			painter.setBrush(color)
			_draw(block)
		painter.setBrush(Qt.GlobalColor.red)
		_draw(self.finish)
		painter.setBrush(Qt.GlobalColor.blue)
		_draw(self.puppet)

		painter.end()
		self.label_canvas.setPixmap(pixmap)

	def keyPressEvent(self, a0):
		direction = DIRECTION.get(util.cast(a0.key()), None)
		if not direction:
			return

		pos = self.puppet[0] + direction[0], self.puppet[1] + direction[1]
		if self.field[pos[0]][pos[1]]:
			self.puppet, pos = pos, self.puppet
			self.draw([self.puppet, pos])
		if self.puppet == self.finish:
			util.dialog("You won", "success")
			return self.restart()


class QtMaze:
	@staticmethod
	def randomized_dfs(self):
		def _dfs(x, y):
			visited[x][y] = True
			directions = list(DIRECTION.values())
			random.shuffle(directions)
			for i, j in directions:
				if not 0 <= x + i < row:
					continue
				if not 0 <= y + j < column:
					continue
				if not visited[x + i][y + j]:
					self.barriers.append(((x, y), (x + i, y + j)))
					_dfs(x + i, y + j)

		row, column = self.spinBox_row.value(), self.spinBox_column.value()
		visited = [[False for _ in range(column)] for _ in range(row)]
		self.barriers.clear()
		_dfs(0, 0)


class QtSolve:
	@staticmethod
	def dfs(self):
		def _dfs(x, y):
			if (x, y) == self.finish:
				return True
			visited[x][y] = True
			for i, j in DIRECTION.values():
				if not QtStatic.is_route(self, x + i, y + j) or visited[x + i][y + j]:
					continue
				self.explored.append((x + i, y + j))
				if _dfs(x + i, y + j):
					self.solution.append((x + i, y + j))
					return True

		visited = [[False for _ in range(self.column_count)] for _ in range(self.row_count)]
		self.explored.clear()
		self.solution.clear()
		_dfs(self.puppet[0], self.puppet[1])

	@staticmethod
	def bfs(self):
		visited = [[False for _ in range(self.column_count)] for _ in range(self.row_count)]
		branches = {}
		self.explored.clear()
		self.solution.clear()

		nodes = [self.puppet]
		while nodes:
			x, y = nodes.pop(0)
			visited[x][y] = True
			if (x, y) == self.finish:
				break

			self.explored.append((x, y))
			for i, j in DIRECTION.values():
				if not QtStatic.is_route(self, x + i, y + j) or visited[x + i][y + j]:
					continue
				nodes.append((x + i, y + j))
				branches[(x + i, y + j)] = (x, y)

		leaf = self.finish
		while leaf in branches:
			self.solution.append(leaf)
			leaf = branches[leaf]


class QtStatic:
	@staticmethod
	def rebuild(self):
		row, column = self.spinBox_row.value(), self.spinBox_column.value()
		self.field = [[WALL for _ in range(column * 2 - 1)] for _ in range(row * 2 - 1)]
		for barrier in self.barriers:
			(x1, y1), (x2, y2) = barrier
			self.field[x1 * 2][y1 * 2] = ROUTE
			self.field[x1 + x2][y1 + y2] = ROUTE
			self.field[x2 * 2][y2 * 2] = ROUTE

		for f in self.field:
			f.insert(0, WALL)
			f.append(WALL)
		self.field.insert(0, [WALL] * (column * 2 + 1))
		self.field.append([WALL] * (column * 2 + 1))

	@staticmethod
	def is_route(self, x, y):
		if not 0 <= x < self.row_count:
			return False
		if not 0 <= y < self.column_count:
			return False
		if not self.field[x][y]:
			return False
		return True


class QtThread(QThread):
	signal_starts = pyqtSignal()
	signal_update = pyqtSignal(list, Qt.GlobalColor)
	signal_finish = pyqtSignal()

	def __init__(self):
		super().__init__()
		util.cast(self.signal_starts).connect(self.starts)
		util.cast(self.signal_update).connect(self.update)
		util.cast(self.signal_finish).connect(self.finish)

	def run(self):
		util.cast(self.signal_starts).emit()
		for e in qt_core.explored:
			util.cast(self.signal_update).emit([e], Qt.GlobalColor.darkGreen)
			self.msleep(1)
		for s in qt_core.solution:
			util.cast(self.signal_update).emit([s], Qt.GlobalColor.green)
			self.msleep(1)
		util.cast(self.signal_finish).emit()

	@staticmethod
	def starts():
		qt_core.pushButton_replay.setEnabled(False)
		qt_core.pushButton_replay.setText("回放中")
		qt_core.pushButton_replay.setIcon(util.icon("loading"))

		qt_core.pushButton_maze.setEnabled(False)
		qt_core.pushButton_solve.setEnabled(False)
		qt_core.pushButton_clear.setEnabled(False)

	@staticmethod
	def update(blocks, color):
		qt_core.draw(blocks, color)

	@staticmethod
	def finish():
		qt_core.pushButton_replay.setEnabled(True)
		qt_core.pushButton_replay.setText("回放")
		qt_core.pushButton_replay.setIcon(util.icon("../maze/replay"))

		qt_core.pushButton_maze.setEnabled(True)
		qt_core.pushButton_solve.setEnabled(True)
		qt_core.pushButton_clear.setEnabled(True)


if __name__ == "__main__":
	sys.setrecursionlimit(5000)
	app = QApplication(sys.argv)
	qt_core = QtCore()
	qt_core.show()
	sys.exit(app.exec())
