from maze_ui import Ui_MainWindow
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
import numpy as np
import random
import sys
import util

DIRECTION = ((0, -1), (0, 1), (-1, 0), (1, 0))
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
	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../maze/logo"))

		util.button(self.pushButton_generate, self.generate, "../maze/generate")
		util.button(self.pushButton_search, self.search, "../maze/search")
		util.button(self.pushButton_replay, self.replay, "../maze/replay")
		self.horizontalSlider.valueChanged.connect(lambda: self.label_maze.setText(f"层级({self.horizontalSlider.value():02})"))
		self.comboBox_generate.addItems(GENERATOR)
		self.comboBox_search.addItems(SEARCHER)
		self.label_canvas.setPixmap(QPixmap(self.label_canvas.size()))

		self.timer = util.timer(10, self.timeout)
		self.labyrinth = self.ariadne = self.minotaur = self.algorithm = None
		self.reached, self.found, self.sz = [], [], {"canvas": 600, "block": 0.0}
		self.generate()

	def generate(self):
		if self.timer.isActive():
			self.timer.stop()
		self.reached.clear()
		self.found.clear()
		self.algorithm = None

		visited = np.zeros((self.horizontalSlider.value(), self.horizontalSlider.value()), dtype=np.uint8)
		shp = visited.shape[0] * 2 + 1, visited.shape[1] * 2 + 1
		self.sz["block"] = round(min(self.sz["canvas"] / shp[1], self.sz["canvas"] / shp[0]), 4)
		self.labyrinth = np.zeros(shp, dtype=np.uint8)

		algorithm = GENERATOR[self.comboBox_generate.currentText()]
		if algorithm == "dfs":
			MyGenerator.dfs((0, 0), visited, self.labyrinth)
		if algorithm == "bfs":
			MyGenerator.bfs(visited, self.labyrinth)

		pixmap = self.label_canvas.pixmap()
		pixmap.fill(Qt.GlobalColor.black)
		self.label_canvas.setPixmap(pixmap)

		self.ariadne, self.minotaur = random.sample(np.argwhere(self.labyrinth == 1).tolist(), 2)
		self.ariadne, self.minotaur = tuple(self.ariadne), tuple(self.minotaur)
		self.display(np.argwhere(self.labyrinth == 1), Qt.GlobalColor.gray)

	def search(self, replay=False):
		if self.timer.isActive():
			self.timer.stop()

		algorithm = SEARCHER[self.comboBox_search.currentText()]
		if self.algorithm == algorithm:
			if not replay:
				self.display(np.argwhere(self.labyrinth == 1), Qt.GlobalColor.gray)
				self.display(self.reached, Qt.GlobalColor.darkGreen)
				self.display(self.found, Qt.GlobalColor.green)
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

		self.reached.remove(self.ariadne) if self.ariadne in self.reached else None
		self.reached.remove(self.minotaur) if self.minotaur in self.reached else None
		self.found.remove(self.ariadne) if self.ariadne in self.found else None
		self.found.remove(self.minotaur) if self.minotaur in self.found else None

		self.display(np.argwhere(self.labyrinth == 1), Qt.GlobalColor.gray)
		self.display(self.reached, Qt.GlobalColor.darkGreen) if not replay else None
		self.display(self.found, Qt.GlobalColor.green) if not replay else None

	def replay(self):
		self.search(replay=True)
		self.display(np.argwhere(self.labyrinth == 1), Qt.GlobalColor.gray)
		self.display(self.reached, QColor(90, 90, 90))

		self.timer.reached = 0
		self.timer.found = 0
		self.timer.start()

	def timeout(self):
		if self.timer.reached < len(self.reached):
			self.display([self.reached[self.timer.reached]], Qt.GlobalColor.darkGreen)
			self.timer.reached += 1
		elif self.timer.found < len(self.found):
			self.display([self.found[self.timer.found]], Qt.GlobalColor.green)
			self.timer.found += 1
		else:
			self.timer.stop()

	def display(self, blocks, color):
		pixmap = self.label_canvas.pixmap()
		with QPainter(pixmap) as painter:
			painter.setPen(Qt.PenStyle.NoPen)
			self.draw(painter, blocks, color)
			self.draw(painter, (self.ariadne,), Qt.GlobalColor.blue)
			self.draw(painter, (self.minotaur,), Qt.GlobalColor.red)
		self.label_canvas.setPixmap(pixmap)

	def draw(self, painter, ps, color):
		s = self.sz["block"]
		painter.setBrush(color)
		for p in ps:
			painter.drawRect(QRectF(p[1] * s, p[0] * s, s, s))


class MyGenerator:
	@staticmethod
	def __construct(pos, i, j, labyrinth):
		px, py = pos[0] * 2 + 1, pos[1] * 2 + 1
		labyrinth[px, py] = 1
		labyrinth[px + i, py + j] = 1
		labyrinth[px + i * 2, py + j * 2] = 1
		return

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
			MyGenerator.__construct(pos, i, j, labyrinth)
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
				MyGenerator.__construct(pos, i, j, labyrinth)
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
		queue, visited[(0, 0)], nodes = [params["ariadne"]], 1, {}
		while queue:
			pos = queue.pop(0)
			if pos == params["minotaur"]:
				break
			params["reached"].append(pos)
			for i, j in DIRECTION:
				p = pos[0] + i, pos[1] + j
				if params["labyrinth"][p] == 0 or visited[p]:
					continue
				visited[pos] = 1
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
