from game2048_ui import Ui_MainWindow
from PyQt6.QtCore import pyqtSignal, QRect, QThread, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import product
from multiprocessing import cpu_count, Pool
import numpy as np
import os
import random
import sys
import util
import mylibrary.myutil as mu


FONT = QFont(QFont().family(), 40, QFont.Weight.Bold)
GROOVE = {(i, j): (j * 115 + 15, i * 115 + 15) for i, j in product(range(4), repeat=2)}

KEY = {Qt.Key.Key_Left: "L", Qt.Key.Key_Right: "R", Qt.Key.Key_Up: "U", Qt.Key.Key_Down: "D"}
MOVEMENT = tuple(KEY.values())
ROTATE = {"L": 0, "R": 2, "U": 1, "D": -1}
TRANS = {"L": lambda x, y: (x, y), "R": lambda x, y: (3 - x, 3 - y), "U": lambda x, y: (y, 3 - x), "D": lambda x, y: (3 - y, x)}

COLOR = {
	0: QColor(205, 193, 180), 1: QColor(238, 228, 218), 2: QColor(237, 224, 200), 3: QColor(242, 177, 121),
	4: QColor(245, 149, 99), 5: QColor(246, 124, 95), 6: QColor(246, 94, 59), 7: QColor(237, 207, 114),
	8: QColor(237, 204, 97), 9: QColor(228, 192, 42), 10: QColor(226, 186, 19), 11: QColor(236, 196, 0),
}


class MyCore(QMainWindow, Ui_MainWindow):
	WEIGHTS = (11, 13, 5, 6, 5)
	board = None
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
		self.board = MyMatrixer.reset()
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
		movement = ExpectimaxAlgorithm.infer(self.board, MyCore.WEIGHTS)
		self.step(movement)

	def botting(self):
		if self.my_thread:
			MyThread.thread_terminate(self)
		else:
			MyThread.thread_run(self)

	def step(self, movement):
		previous = self.board.copy()
		self.board, trails = MyMatrixer.moving(self.board, movement)

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


class MyMatrixer:
	@staticmethod
	def moving(board, movement):
		rotate, trans = ROTATE[movement], TRANS[movement]
		board = np.rot90(board, rotate)
		board, trails = MyMatrixer.merge(board, trans)
		board = np.rot90(board, -rotate)
		return board, trails

	@staticmethod
	def merge(board, trans):
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

		board = np.array([s + [0] * (4 - len(s)) for s in subsequent])
		return board, tuple(trails[::])

	@staticmethod
	def reset():
		board = np.zeros((4, 4), dtype=np.int8)
		MyMatrixer.add(board)
		MyMatrixer.add(board)
		return board

	@staticmethod
	def add(board):
		empty_cells = tuple(np.argwhere(board == 0))
		empty_pos = tuple(random.choice(empty_cells))
		board[empty_pos] = 1 if random.random() < 0.9 else 2

	@staticmethod
	def win(board):
		return 11 in board

	@staticmethod
	def lose(board):
		return (0 not in board) and (0 not in np.diff(board)) and (0 not in np.diff(board.T))


class MyDisplayer:
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
			painter.setFont(FONT)
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
			painter.setFont(FONT)
			for ((sx, sy), (ex, ey)), tile in self.timer.property("trails"):
				groove = int(sx + (ex - sx) * offset), int(sy + (ey - sy) * offset)
				MyDisplayer.draw(painter, tile, groove)
		self.label.setPixmap(pixmap)

	@staticmethod
	def draw(painter, tile, groove):
		rect = QRect(*groove, 100, 100)
		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(COLOR[tile])
		painter.drawRect(rect)
		if tile:
			painter.setPen(QColor(118, 110, 101))
			painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(2 ** tile))


class MyThread(QThread):
	signal_update = pyqtSignal()
	running = True

	def __init__(self):
		super().__init__()
		util.cast(self.signal_update).connect(self.update)

	def run(self):
		while self.running and not MyMatrixer.win(my_core.board) and not MyMatrixer.lose(my_core.board):
			util.cast(self.signal_update).emit()
			self.msleep(500)

	@staticmethod
	def update():
		movement = ExpectimaxAlgorithm.infer(my_core.board, MyCore.WEIGHTS)
		my_core.step(movement)

	@staticmethod
	def thread_run(self):
		self.toolButton_botting.setIcon(util.icon("../game2048/terminate"))
		self.toolButton_botting.setToolTip("取消AI托管")

		self.my_thread = MyThread()
		self.my_thread.start()

	@staticmethod
	def thread_terminate(self):
		self.toolButton_botting.setIcon(util.icon("../game2048/brain"))
		self.toolButton_botting.setToolTip("AI托管")

		self.my_thread.running = False
		self.my_thread.wait()
		self.my_thread = None


class ExpectimaxAlgorithm:
	@staticmethod
	def evaluate(board, weights):
		potential_merge = 0
		for movement in MOVEMENT:
			subsequent, _ = MyMatrixer.moving(board.copy(), movement)
			combined = np.concatenate((subsequent, subsequent.T))
			potential_merge += sum(np.count_nonzero(np.diff(c[c != 0]) == 0) for c in combined)

		smoothness_horizontal = np.abs(np.diff(board))
		smoothness_horizontal[board[:, :-1] * board[:, 1:] == 0] = 0
		smoothness_vertical = np.abs(np.diff(board.T))
		smoothness_vertical[board.T[:, :-1] * board.T[:, 1:] == 0] = 0
		smoothness = - np.sum(smoothness_horizontal) - np.sum(smoothness_vertical)

		return (
			weights[0] * np.sum(board == 0) +
			weights[1] * ((np.argmax(board) in (0, 3, 12, 15)) * np.max(board)) +
			weights[2] * (np.sum(board) - np.sum(board[1:-1,1:-1])) +
			weights[3] * potential_merge +
			weights[4] * smoothness
		)

	@staticmethod
	def search(board, weights, depth, max_depth):
		if MyMatrixer.lose(board):
			return -1000, None
		if depth >= max_depth:
			return ExpectimaxAlgorithm.evaluate(board, weights), None
		if depth % 2 == 0:
			best_score, best_movement = -np.inf, None
			for movement in MOVEMENT:
				subsequent, _ = MyMatrixer.moving(board, movement)
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
	def infer(board, weights):
		max_depth = 3
		_, movement = ExpectimaxAlgorithm.search(board, weights, 0, max_depth)
		return movement


class GeneticAlgorithm:
	GENE_SIZE, GENE_COUNT = 4, 5
	GENE_TYPE, DNA_SIZE = 2 ** GENE_SIZE, GENE_SIZE * GENE_COUNT

	POPULATION_SIZE = 80
	POPULATION_PATH = util.join_path(util.RESOURCE, "game2048", "population.pkl")

	ELITE_SIZE, INFERIOR_SIZE = 16, 20
	COMMON_SIZE = POPULATION_SIZE - ELITE_SIZE - INFERIOR_SIZE

	CROSSOVER_RATE = 0.8
	MUTATION_RATE = 0.1

	EPOCH = 50

	STEP_LIMIT = 1500

	@staticmethod
	def _encode_gene():
		gene = random.randint(0, GeneticAlgorithm.GENE_TYPE - 1)
		return f"{bin(gene)[2:]:>0{GeneticAlgorithm.GENE_SIZE}}"

	@staticmethod
	def _encode_dna():
		return "".join(GeneticAlgorithm._encode_gene() for _ in range(GeneticAlgorithm.GENE_COUNT))

	@staticmethod
	def _decode_gene(dna, i):
		gene = dna[i * GeneticAlgorithm.GENE_SIZE:(i + 1) * GeneticAlgorithm.GENE_SIZE]
		return int(gene, 2) + 1

	@staticmethod
	def _decode_dna(dna):
		return tuple(GeneticAlgorithm._decode_gene(dna, i) for i in range(GeneticAlgorithm.GENE_COUNT))

	@staticmethod
	def _log(epoch, i, step, score, weights):
		print(
			f"EPOCH[{epoch + 1:2}/{GeneticAlgorithm.EPOCH}] "
			f"DNA[{i + 1:2}/{GeneticAlgorithm.POPULATION_SIZE}] "
			f"STEP[{step:4}] SCORE[{score:5}] {weights}"
		)

	@staticmethod
	def _fit(epoch, i, weights):
		board, step = MyMatrixer.reset(), 0
		while True:
			if MyMatrixer.win(board):
				score = (GeneticAlgorithm.STEP_LIMIT - step) + 10000
				GeneticAlgorithm._log(epoch, i, step, score, weights)
				return score
			if MyMatrixer.lose(board) or step >= GeneticAlgorithm.STEP_LIMIT:
				score = step + np.max(board) * 20
				GeneticAlgorithm._log(epoch, i, step, score, weights)
				return score

			movement = ExpectimaxAlgorithm.infer(board, weights)
			previous = board.copy()
			board, _ = MyMatrixer.moving(board, movement)

			if not np.array_equal(board, previous):
				MyMatrixer.add(board)
			step += 1

	@staticmethod
	def _evaluate_task(params):
		dna, epoch, i = params
		weights = GeneticAlgorithm._decode_dna(dna)
		fitness = GeneticAlgorithm._fit(epoch, i, weights)
		return dna, fitness

	@staticmethod
	@mu.Decorator.timing
	def _evaluate(population, epoch, pool):
		return dict(pool.imap_unordered(GeneticAlgorithm._evaluate_task, ((dna, epoch, i) for i, dna in enumerate(population))))

	@staticmethod
	def _select(fitnesses):
		fs = sorted(list(fitnesses.items()), key=lambda x: x[1], reverse=True)[:-GeneticAlgorithm.INFERIOR_SIZE]
		elites = [f[0] for f in fs[:GeneticAlgorithm.ELITE_SIZE]]
		commons = [f[0] for f in fs[GeneticAlgorithm.ELITE_SIZE:]]
		return elites, commons

	@staticmethod
	def _crossover(population):
		for i in range(0, len(population) // 2 * 2, 2):
			if random.random() < GeneticAlgorithm.CROSSOVER_RATE:
				dna1, dna2 = population[i], population[i + 1]
				population[i], population[i + 1] = "", ""
				for j in range(GeneticAlgorithm.DNA_SIZE):
					crossover_point = random.random()
					population[i] += dna1[j] if crossover_point < 0.5 else dna2[j]
					population[i + 1] += dna2[j] if crossover_point < 0.5 else dna1[j]
		return population

	@staticmethod
	def _mutate(population):
		return ["".join(
			("0" if int(locus) else "1") if random.random() < GeneticAlgorithm.MUTATION_RATE else locus
			for locus in population[i]
		) for i in range(len(population))]

	@staticmethod
	def train():
		with Pool(processes=cpu_count()) as pool:
			if os.path.exists(GeneticAlgorithm.POPULATION_PATH):
				population = util.FileIO.read(GeneticAlgorithm.POPULATION_PATH).keys()
			else:
				population = {GeneticAlgorithm._encode_dna(): 0 for _ in range(GeneticAlgorithm.POPULATION_SIZE)}

			for epoch in range(GeneticAlgorithm.EPOCH):
				fitnesses = GeneticAlgorithm._evaluate(population, epoch, pool)
				util.FileIO.write(GeneticAlgorithm.POPULATION_PATH, fitnesses)
				print(f"EPOCH:{epoch + 1:2} AVG:{sum(fitnesses.values()) // len(fitnesses):3} {fitnesses}")

				population_elite, population_common = GeneticAlgorithm._select(fitnesses)
				population_crossovered = GeneticAlgorithm._crossover(population_common)
				population_mutated = GeneticAlgorithm._mutate(population_crossovered)
				population_newborn = [GeneticAlgorithm._encode_dna() for _ in range(GeneticAlgorithm.INFERIOR_SIZE)]
				population = population_elite + population_mutated + population_newborn


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
