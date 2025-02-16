from game2048_ui import Ui_MainWindow
from PyQt6.QtCore import pyqtSignal, QRect, QThread, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from functools import lru_cache
from itertools import product
from multiprocessing import cpu_count, Pool
import numpy as np
import os
import random
import sys
import time
import util


import mylibrary.myutil as mu

GROOVE = {(i, j): (j * 115 + 15, i * 115 + 15) for i, j in product(range(4), repeat=2)}
KEY = {Qt.Key.Key_Left: "L", Qt.Key.Key_Right: "R", Qt.Key.Key_Up: "U", Qt.Key.Key_Down: "D"}
MOVEMENT = tuple(KEY.values())


PATH_MERGE = util.join_path(util.RESOURCE, "game2048", "cache_merge.pkl")
PATH_MERGE_V = util.join_path(util.RESOURCE, "game2048", "cache_merge_v.pkl")
PATH_MERGE_POTENTIAL = util.join_path(util.RESOURCE, "game2048", "cache_merge_potential.pkl")

CACHE_MERGE = util.FileIO.read(PATH_MERGE)
CACHE_MERGE_V = util.FileIO.read(PATH_MERGE_V)
CACHE_MERGE_POTENTIAL = util.FileIO.read(PATH_MERGE_POTENTIAL)


class MyCore(QMainWindow, Ui_MainWindow):
	WEIGHT = (19, 17, 15, 11, 30)
	board = np.zeros((4, 4), dtype=np.int8)
	skeleton, my_thread, mouse_pos = None, None, None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../game2048/2048"))

		self.timer = QTimer()
		self.timer.setInterval(15)
		util.cast(self.timer).timeout.connect(lambda: MyDisplayer.animate(self))

		util.button(self.pushButton, self.restart)
		util.button(self.toolButton_hinting, self.hinting, "../game2048/bulb", tip="提示", ico_size=24)
		util.button(self.toolButton_botting, self.botting, "../game2048/brain", tip="AI托管", ico_size=24)
		self.label.mousePressEvent = self.mouse_press
		self.label.mouseReleaseEvent = self.mouse_release

		MyDisplayer.skeletonize(self)
		self.restart()

	def restart(self):
		if self.timer.isActive():
			self.timer.stop()
		if self.my_thread:
			MyThread.thread_terminate(self)
		MyMatrixer.reset(self.board)
		MyDisplayer.display(self)

	def keyPressEvent(self, a0):
		if self.timer.isActive():
			return
		if self.my_thread:
			return
		if a0.key() in KEY:
			movement = KEY[util.cast(a0.key())]
			self.step(movement)

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
		movement = ExpectimaxAlgorithm.infer(self.board, MyCore.WEIGHT)
		self.step(movement)

	def botting(self):
		if self.my_thread:
			MyThread.thread_terminate(self)
		else:
			MyThread.thread_run(self)

	def step(self, movement):
		previous = self.board.copy()

		rotate, trans = {"L": 0, "R": 2, "U": 1, "D": -1}[movement], MyDisplayer.TRANS[movement]
		self.board = np.rot90(self.board, rotate)
		trails = MyDisplayer.track(self.board, trans)
		self.board = np.rot90(self.board, -rotate)


		self.board = MyMatrixer.moving(self.board, movement)

		self.timer.setProperty("frame", 0)
		self.timer.setProperty("trails", trails)
		self.timer.start()

		if MyMatrixer.win(self.board):
			util.dialog("You win", "success")
			return self.restart()
		if not np.array_equal(self.board, previous):
			MyMatrixer.add(self.board)
		if MyMatrixer.lose(self.board):
			util.dialog("You lose", "error")
			return self.restart()


class MyDisplayer:
	FONT = QFont(QFont().family(), 40, QFont.Weight.Bold)
	COLOR = {
		0: QColor(205, 193, 180), 1: QColor(238, 228, 218), 2: QColor(237, 224, 200), 3: QColor(242, 177, 121),
		4: QColor(245, 149, 99), 5: QColor(246, 124, 95), 6: QColor(246, 94, 59), 7: QColor(237, 207, 114),
		8: QColor(237, 204, 97), 9: QColor(228, 192, 42), 10: QColor(226, 186, 19), 11: QColor(236, 196, 0),
	}


	TRANS = {
		"L": lambda x, y: (x, y), "R": lambda x, y: (3 - x, 3 - y),
		"U": lambda x, y: (y, 3 - x), "D": lambda x, y: (3 - y, x)
	}

	@staticmethod
	def skeletonize(self):
		self.skeleton = QPixmap(475, 475)
		self.skeleton.fill(QColor(187, 173, 160))
		with QPainter(self.skeleton) as painter:
			for groove in GROOVE.values():
				MyDisplayer.draw(painter, 0, groove)

	@staticmethod
	def display(self):
		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(MyDisplayer.FONT)
			for pos, groove in GROOVE.items():
				MyDisplayer.draw(painter, self.board[pos], groove)
		self.label.setPixmap(pixmap)

	@staticmethod
	def animate(self):
		self.timer.setProperty("frame", self.timer.property("frame") + 1)
		if self.timer.property("frame") > 10:
			self.timer.stop()
			return MyDisplayer.display(self)

		offset = self.timer.property("frame") / 10
		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(MyDisplayer.FONT)
			for ((sx, sy), (ex, ey)), tile in self.timer.property("trails"):
				groove = int(sx + (ex - sx) * offset), int(sy + (ey - sy) * offset)
				MyDisplayer.draw(painter, tile, groove)
		self.label.setPixmap(pixmap)

	@staticmethod
	def draw(painter, tile, groove):
		rect = QRect(*groove, 100, 100)
		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(MyDisplayer.COLOR[tile])
		painter.drawRect(rect)
		if tile:
			painter.setPen(QColor(118, 110, 101))
			painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(2 ** tile))

	@staticmethod
	def track(board, trans):
		subsequent = [[] for _ in range(4)]
		merged = [False] * 4
		trails = []

		for i, j in product(range(4), repeat=2):
			tile = board[i, j]
			if tile == 0:
				continue

			if subsequent[i] and subsequent[i][-1] == tile and not merged[i]:
				subsequent[i][-1] += 1
				merged[i] = True
			else:
				subsequent[i].append(tile)
				merged[i] = False

			trail = GROOVE[trans(i, j)], GROOVE[trans(i, len(subsequent[i]) - 1)]
			trails.append((trail, tile))

		return tuple(trails[::])


class MyThread(QThread):
	signal_update = pyqtSignal()
	dummy = None
	running = True

	def __init__(self):
		super().__init__()
		util.cast(self.signal_update).connect(self.update)

	def run(self):
		while self.running and not MyMatrixer.win(self.dummy.board) and not MyMatrixer.lose(self.dummy.board):
			util.cast(self.signal_update).emit()
			self.msleep(200)

	def update(self):
		movement = ExpectimaxAlgorithm.infer(self.dummy.board, MyCore.WEIGHT)
		self.dummy.step(movement)

	@staticmethod
	def thread_run(self):
		self.toolButton_botting.setIcon(util.icon("../game2048/terminate"))
		self.toolButton_botting.setToolTip("取消AI托管")

		self.my_thread = MyThread()
		self.my_thread.dummy = self
		self.my_thread.start()

	@staticmethod
	def thread_terminate(self):
		self.toolButton_botting.setIcon(util.icon("../game2048/brain"))
		self.toolButton_botting.setToolTip("AI托管")

		self.my_thread.running = False
		self.my_thread.wait()
		self.my_thread = None


class MyMatrixer:
	@staticmethod
	def moving(board, movement):
		board = board.T if movement in "UD" else board
		for i in range(4):
			board[i] = (CACHE_MERGE if movement in "LU" else CACHE_MERGE_V)[board[i].tobytes()]
		return board.T if movement in "UD" else board

	@staticmethod
	def reset(board):
		board.fill(0)
		MyMatrixer.add(board)
		MyMatrixer.add(board)

	@staticmethod
	def add(board):
		empty_pos = random.choice(np.argwhere(board == 0))
		board[tuple(empty_pos)] = 1 if random.randint(1, 10) <= 9 else 2

	@staticmethod
	def win(board):
		return 11 in board

	@staticmethod
	def lose(board):
		return (0 not in board) and (0 not in np.diff(board)) and (0 not in np.diff(board.T))




class ExpectimaxAlgorithm:
	@staticmethod
	#@mu.Decorator.timing
	#@mu.Decorator.performance
	def infer(board, weights):
		max_depth = 3 if np.max(board) >= 8 else 2

		_, movement = ExpectimaxAlgorithm.search(board, weights, 0, max_depth)
		#print(ExpectimaxAlgorithm._search1.cache_info(), "_search")
		return movement


	@staticmethod
	def search(board, weights, depth, max_depth):
		if max_depth == 3:
			return ExpectimaxAlgorithm._search_cache(board.tobytes(), weights, depth, max_depth)
		else:
			return ExpectimaxAlgorithm._search_nocache(board, weights, depth, max_depth)

	@staticmethod
	@lru_cache(maxsize=None)
	def _search_cache(board, weights, depth, max_depth):
		board = np.frombuffer(board, dtype=np.int8).reshape((4, 4))
		return ExpectimaxAlgorithm._search_nocache(board, weights, depth, max_depth)

	@staticmethod
	def _search_nocache(board, weights, depth, max_depth):
		if MyMatrixer.lose(board):
			return -1000, None
		if depth >= max_depth:
			return ExpectimaxAlgorithm.evaluate(board, weights), None
		if depth % 2 == 0:
			best_score, best_movement = -np.inf, None
			for movement in MOVEMENT:
				subsequent = board.copy()
				subsequent = MyMatrixer.moving(subsequent, movement)
				if not np.array_equal(board, subsequent):
					score, _ = ExpectimaxAlgorithm.search(subsequent, weights, depth + 1, max_depth)
					if score >= best_score:
						best_score, best_movement = score, movement
			return best_score, best_movement
		else:
			empty_cells = tuple(np.argwhere(board == 0))
			if not empty_cells:
				return ExpectimaxAlgorithm.evaluate(board, weights)

			probs = {2: 0.9 / len(empty_cells), 4: 0.1 / len(empty_cells)}
			best_score = 0
			for empty_cell in empty_cells:
				for tile, prob in probs.items():
					subsequent = board.copy()
					subsequent[tuple(empty_cell)] = tile
					score, _ = ExpectimaxAlgorithm.search(subsequent, weights, depth + 1, max_depth)
					best_score += prob * score
			return best_score, None

	@staticmethod
	def evaluate(board, weights):
		potential_merge = 0
		for movement in MOVEMENT:
			subsequent = board.copy()
			subsequent = MyMatrixer.moving(subsequent, movement)
			potential_merge += sum(CACHE_MERGE_POTENTIAL[s.tobytes()] for s in np.vstack((subsequent, subsequent.T)))

		diff_h = np.abs(board[:, :-1] - board[:, 1:])
		mask_h = (board[:, :-1] != 0) & (board[:, 1:] != 0)
		diff_v = np.abs(board[:-1, :] - board[1:, :])
		mask_v = (board[:-1, :] != 0) & (board[1:, :] != 0)
		smoothness = - np.sum(diff_h * mask_h) - np.sum(diff_v * mask_v)

		return (
			weights[0] * np.sum(board == 0) +
			weights[1] * ((np.argmax(board) in (0, 3, 12, 15)) * np.max(board)) +
			weights[2] * (np.sum(board) - np.sum(board[1:-1,1:-1])) +
			weights[3] * potential_merge +
			weights[4] * smoothness
		)


class MyPrecomputation:
	@staticmethod
	def compute_merge():
		cache_merge, cache_merge_v = {}, {}
		for tiles in product(range(12), repeat=4):
			t, merged = [], False
			for tile in tiles:
				if tile == 0:
					continue
				if t and t[-1] == tile and not merged:
					t[-1] += 1
					merged = True
				else:
					t.append(tile)
					merged = False
			cache = np.array(t + [0] * (4 - len(t)))
			cache_merge[np.array(tiles, dtype=np.int8).tobytes()] = cache
			cache_merge_v[np.array(tiles[::-1], dtype=np.int8).tobytes()] = cache[::-1]
		util.FileIO.write(PATH_MERGE, cache_merge)
		util.FileIO.write(PATH_MERGE_V, cache_merge_v)

	@staticmethod
	def compute_merge_potential():
		cache_merge_potential = {}
		for tiles in product(range(12), repeat=4):
			t = np.array(tiles)
			cache_merge_potential[np.array(tiles, dtype=np.int8).tobytes()] = np.count_nonzero(np.diff(t[t != 0]) == 0)
		util.FileIO.write(PATH_MERGE_POTENTIAL, cache_merge_potential)


class GeneticAlgorithm:
	GENE, DNA = 30, 5
	EPOCH, POPULATION = 10, 80
	CROSSOVER, MUTATION = 0.6, 0.1

	ELITE, INFERIOR = 16, 8
	COMMON = POPULATION - ELITE - INFERIOR
	
	STEP = 1500
	EVALUATION = util.join_path(util.RESOURCE, "game2048", "evaluation.pkl")

	@staticmethod
	def train():
		board = MyCore.board.copy()
		with Pool(processes=cpu_count()) as pool:
			if not os.path.exists(GeneticAlgorithm.EVALUATION):
				population = [GeneticAlgorithm.get_dna() for _ in range(GeneticAlgorithm.POPULATION)]
			else:
				population = list(util.FileIO.read(GeneticAlgorithm.EVALUATION))

			for epoch in range(GeneticAlgorithm.EPOCH):
				tictoc = time.time()
				evaluation = dict(pool.imap_unordered(GeneticAlgorithm.fit, ((board, dna, epoch, i) for i, dna in enumerate(population))))
				util.FileIO.write(GeneticAlgorithm.EVALUATION, evaluation)
				print(f"TICTOC: {round(time.time() - tictoc, 2)} s")
				print(sorted(evaluation.items(), key=lambda x: x[1], reverse=True))

				population_elite, population_common = GeneticAlgorithm.select(evaluation)
				population_crossovered = GeneticAlgorithm.crossover(population_common)
				population_mutated = GeneticAlgorithm.mutate(population_crossovered)
				population_newborn = [GeneticAlgorithm.get_dna() for _ in range(GeneticAlgorithm.INFERIOR)]
				population = population_elite + population_mutated + population_newborn

	@staticmethod
	def get_population():
		return [GeneticAlgorithm.get_dna() for _ in range(GeneticAlgorithm.POPULATION)]

	@staticmethod
	def get_dna():
		return tuple(GeneticAlgorithm.get_gene() for _ in range(GeneticAlgorithm.DNA))

	@staticmethod
	def get_gene():
		return random.randint(1, GeneticAlgorithm.GENE)

	@staticmethod
	def fit(params):
		board, weights, epoch, i = params
		fitness = GeneticAlgorithm._fit(board, weights, epoch, i, 1, 0)
		extra = 4 if fitness >= 10000 else 2
		for j in range(extra):
			fitness += GeneticAlgorithm._fit(board, weights, epoch, i, j + 2, extra + 1)
		return weights, fitness // extra

	@staticmethod
	def _fit(board, weights, epoch, i, j, extra):
		MyMatrixer.reset(board)
		step = 0

		while True:
			step += 1
			if MyMatrixer.win(board):
				fitness = (GeneticAlgorithm.STEP - step) + 10000
				GeneticAlgorithm.log(epoch, i, j, extra, step, fitness, weights)
				return fitness
			if MyMatrixer.lose(board) or step >= GeneticAlgorithm.STEP:
				fitness = (GeneticAlgorithm.STEP - step) + np.max(board) * 500
				GeneticAlgorithm.log(epoch, i, j, extra, step, fitness, weights)
				return fitness

			movement = ExpectimaxAlgorithm.infer(board, weights)
			previous = board.copy()
			board = MyMatrixer.moving(board, movement)
			if not np.array_equal(board, previous):
				MyMatrixer.add(board)

	@staticmethod
	def select(evaluation):
		evaluation = sorted(evaluation.items(), key=lambda x: x[1], reverse=True)[:-GeneticAlgorithm.INFERIOR]
		elites = [ev[0] for ev in evaluation[:GeneticAlgorithm.ELITE]]
		commons = [ev[0] for ev in evaluation[GeneticAlgorithm.ELITE:]]
		return elites, commons

	@staticmethod
	def crossover(population):
		for i in range(0, len(population) // 2 * 2, 2):
			if random.random() < GeneticAlgorithm.CROSSOVER:
				dna1 = list(population[i])
				dna2 = list(population[i + 1])
				for j in range(GeneticAlgorithm.DNA):
					if random.random() < 0.5:
						dna1[j], dna2[j] = dna2[j], dna1[j]
				population[i] = tuple(dna1)
				population[i + 1] = tuple(dna2)
		return population

	@staticmethod
	def mutate(population):
		return [tuple(GeneticAlgorithm.get_gene() if random.random() < GeneticAlgorithm.MUTATION else gene for gene in dna) for dna in population]

	@staticmethod
	def log(epoch, i, j, extra, step, fitness, dna):
		print(
			f"EPOCH[{epoch + 1:2}/{GeneticAlgorithm.EPOCH}] "
			f"DNA[{i + 1:2}/{GeneticAlgorithm.POPULATION}] "
			f"GAME[{j}/{extra}] "
			f"STEP[{step:4}] FITNESS[{fitness:5}] {dna}"
		)



if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
