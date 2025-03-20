from maze_ui import Ui_MainWindow
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
import numpy as np
import random
import sys
import util

DIRECTION = ((-1, 0), (1, 0), (0, -1), (0, 1))
GENERATOR = {
	"深度优先(DFS)": "dfs",
	"广度优先(BFS)": "bfs",
	# "随机Kruskal",
	# "Prim",
	# "递归分割"
}
SEARCHER = {
	"深度优先(DFS)": "dfs",
	"广度优先(BFS)": "bfs",
	# "深度受限(DLS)": "",
	# "迭代加深(IDS)": "",
	# "双向搜索(BS)": "",
	# "爬山法/贪婪最佳优先搜索(HCS)": "",
	# "最佳优先搜索(BFS)": "",
	# "集束搜索(BeamS)": "",
	# "GBFS": "",
	# "统一代价搜索(UCS)": "",
	# "A*": ""
}


class MyCore(QMainWindow, Ui_MainWindow):
	labyrinth, ariadne, minotaur = None, None, None
	reached, found, algorithm = [], [], None
	block_size = None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../maze/logo"))

		util.button(self.pushButton_generate, self.generate, "")
		util.button(self.pushButton_search, self.search, "")
		util.button(self.pushButton_replay, self.replay, "")
		self.horizontalSlider_row.valueChanged.connect(lambda: self.label_row.setText(f"行数({self.horizontalSlider_row.value():02})"))
		self.horizontalSlider_col.valueChanged.connect(lambda: self.label_col.setText(f"列数({self.horizontalSlider_col.value():02})"))

		self.timer = util.timer(10, self.timeout)
		self.comboBox_generate.addItems(GENERATOR)
		self.comboBox_search.addItems(SEARCHER)
		self.widgets = (
			self.horizontalSlider_row, self.horizontalSlider_col, self.comboBox_generate, self.comboBox_search,
			self.pushButton_generate, self.pushButton_search, self.pushButton_replay
		)
		self.generate()

	def generate(self):
		self.reached.clear()
		self.found.clear()
		self.algorithm = None

		r, c = self.horizontalSlider_row.value(), self.horizontalSlider_col.value()
		row_count, col_count = r * 2 + 1, c * 2 + 1
		visited = np.zeros((r, c), dtype=np.uint8)
		self.labyrinth = np.zeros((row_count, col_count), dtype=np.uint8)

		frame_size = self.frame.minimumWidth(), self.frame.minimumHeight()
		self.block_size = round(min(frame_size[0] / col_count, frame_size[1] / row_count), 4)
		self.label_canvas.setFixedSize(int(col_count * self.block_size), int(row_count * self.block_size))

		pixmap = QPixmap(self.label_canvas.size())
		pixmap.fill(Qt.GlobalColor.black)
		self.label_canvas.setPixmap(pixmap)

		algorithm = GENERATOR[self.comboBox_generate.currentText()]
		if algorithm == "dfs":
			MyGenerator.dfs((0, 0), visited, self.labyrinth)
		if algorithm == "bfs":
			MyGenerator.bfs(visited, self.labyrinth)

		self.ariadne, self.minotaur = random.sample(np.argwhere(self.labyrinth == 1).tolist(), 2)
		self.ariadne, self.minotaur = tuple(self.ariadne), tuple(self.minotaur)
		self.display(np.argwhere(self.labyrinth == 1))
		self.progressBar_reached.setValue(0)
		self.progressBar_found.setValue(0)

	def search(self, replay=False):
		algorithm = SEARCHER[self.comboBox_search.currentText()]
		if self.algorithm == algorithm:
			return
		self.reached.clear()
		self.found.clear()

		params = {
			"labyrinth": self.labyrinth,
			"ariadne": self.ariadne,
			"minotaur": self.minotaur,
			"reached": self.reached,
			"found": self.found
		}

		self.algorithm = algorithm
		if self.algorithm == "dfs":
			MySearcher.dfs(self.ariadne, np.zeros(self.labyrinth.shape, dtype=np.uint8), params)
		if self.algorithm == "bfs":
			MySearcher.bfs(np.zeros(self.labyrinth.shape, dtype=np.uint8), params)

		self.progressBar_reached.setMaximum(len(self.reached))
		self.progressBar_reached.setValue(self.progressBar_reached.maximum())
		self.progressBar_found.setMaximum(len(self.found))
		self.progressBar_found.setValue(self.progressBar_found.maximum())

		self.reached.remove(self.ariadne) if self.ariadne in self.reached else None
		self.reached.remove(self.minotaur) if self.minotaur in self.reached else None
		self.found.remove(self.ariadne) if self.ariadne in self.found else None
		self.found.remove(self.minotaur) if self.minotaur in self.found else None

		self.display(np.argwhere(self.labyrinth == 1))
		self.display(self.reached, color=Qt.GlobalColor.darkGreen) if not replay else None
		self.display(self.found, color=Qt.GlobalColor.green) if not replay else None

	def replay(self):
		self.search(replay=True)
		self.display(np.argwhere(self.labyrinth == 1))

		for widget in self.widgets:
			widget.setEnabled(False)
		self.progressBar_reached.setValue(0)
		self.progressBar_reached.setMaximum(len(self.reached))
		self.progressBar_found.setValue(0)
		self.progressBar_found.setMaximum(len(self.found))

		self.timer.reached = 0
		self.timer.found = 0
		self.timer.start()

	def timeout(self):
		if self.timer.reached < len(self.reached):
			self.display([self.reached[self.timer.reached]], color=Qt.GlobalColor.darkGreen)
			self.timer.reached += 1
			self.progressBar_reached.setValue(self.timer.reached)
		elif self.timer.found < len(self.found):
			self.display([self.found[self.timer.found]], color=Qt.GlobalColor.green)
			self.timer.found += 1
			self.progressBar_found.setValue(self.timer.found)
		else:
			self.timer.stop()
			for widget in self.widgets:
				widget.setEnabled(True)

	def display(self, blocks, color=Qt.GlobalColor.gray):
		size = self.block_size
		size_ariadne = self.ariadne[1] * size, self.ariadne[0] * size
		size_minotaur = self.minotaur[1] * size, self.minotaur[0] * size

		pixmap = self.label_canvas.pixmap()
		with QPainter(pixmap) as painter:
			painter.setPen(Qt.PenStyle.NoPen)
			painter.setBrush(color)
			for block in blocks:
				painter.drawRect(QRectF(block[1] * size, block[0] * size, size, size))
			painter.setBrush(Qt.GlobalColor.blue)
			painter.drawRect(QRectF(*size_ariadne, size, size))
			painter.setBrush(Qt.GlobalColor.red)
			painter.drawRect(QRectF(*size_minotaur, size, size))
		self.label_canvas.setPixmap(pixmap)


class MyGenerator:
	@staticmethod
	def __construct(p, i, j, visited, labyrinth):
		if not 0 <= p[0] < visited.shape[0]:
			return False
		if not 0 <= p[1] < visited.shape[1]:
			return False
		if visited[p]:
			return False
		px, py = (p[0] - i) * 2 + 1, (p[1] - j) * 2 + 1
		labyrinth[px, py] = 1
		labyrinth[px + i, py + j] = 1
		labyrinth[px + i * 2, py + j * 2] = 1
		return True

	@staticmethod
	def dfs(pos, visited, labyrinth):
		visited[pos] = 1
		for i, j in random.sample(DIRECTION, 4):
			p = pos[0] + i, pos[1] + j
			if not 0 <= p[0] < visited.shape[0]:
				continue
			if not 0 <= p[1] < visited.shape[1]:
				continue
			if visited[p]:
				continue
			px, py = pos[0] * 2 + 1, pos[1] * 2 + 1
			labyrinth[px, py] = 1
			labyrinth[px + i, py + j] = 1
			labyrinth[px + i * 2, py + j * 2] = 1
			MyGenerator.dfs(p, visited, labyrinth)

	@staticmethod
	def bfs(visited, labyrinth):
		queue, visited[(0, 0)] = {(0, 0)}, 1
		while queue:
			pos = random.choice(tuple(queue))
			queue.remove(pos)
			for i, j in random.sample(DIRECTION, 4):
				p = pos[0] + i, pos[1] + j
				if not 0 <= p[0] < visited.shape[0]:
					continue
				if not 0 <= p[1] < visited.shape[1]:
					continue
				if visited[p]:
					continue
				px, py = pos[0] * 2 + 1, pos[1] * 2 + 1
				labyrinth[px, py] = 1
				labyrinth[px + i, py + j] = 1
				labyrinth[px + i * 2, py + j * 2] = 1
				visited[p] = 1
				queue.add(p)


class MySearcher:
	@staticmethod
	def dfs(pos, visited, params):
		if pos == params["minotaur"]:
			return True
		visited[pos] = 1
		for i, j in DIRECTION:
			p = pos[0] + i, pos[1] + j
			if params["labyrinth"][p] == 0 or visited[p]:
				continue
			params["reached"].append(p)
			if MySearcher.dfs(p, visited, params):
				params["found"].append(p)
				return True
		return False

	@staticmethod
	def bfs(visited, params):
		queue, nodes = [params["ariadne"]], {}
		while queue:
			pos = queue.pop(0)
			if pos == params["minotaur"]:
				break
			visited[pos] = 1
			params["reached"].append(pos)
			for i, j in DIRECTION:
				p = pos[0] + i, pos[1] + j
				if params["labyrinth"][p] == 0 or visited[p]:
					continue
				queue.append(p)
				nodes[p] = pos
		node = params["minotaur"]
		while node in nodes:
			params["found"].append(node)
			node = nodes[node]


if __name__ == "__main__":
	sys.setrecursionlimit(10000)
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
