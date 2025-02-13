import os.path

from game2048_ui import Ui_MainWindow
from PyQt6.QtCore import pyqtSignal, QRect, QThread, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import product
from multiprocessing import cpu_count, Pool
import numpy as np
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

GRADIENT = np.array([
	[0.6, 0.5, 0.4, 0.3],
	[0.5, 0.4, 0.3, 0.2],
	[0.4, 0.3, 0.2, 0.1],
	[0.3, 0.2, 0.1, 0.0]
])



WEIGHTS = (3, 5, 2, 2, 2, 2)



class MyCore(QMainWindow, Ui_MainWindow):
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
		movement = ExpectimaxAlgorithm.infer(self.board, WEIGHTS)
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
		movement = ExpectimaxAlgorithm.infer(my_core.board, WEIGHTS)
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
		board_t = board.T
		board_combined = np.concatenate((board, board_t))

		empty = np.sum(board == 0)
		merge = sum(np.count_nonzero(np.diff(b[b != 0]) == 0) for b in board_combined)
		gradient = np.sum(board * GRADIENT)
		distribution = - np.var(board, axis=0).sum() - np.var(board, axis=1).sum()

		monotonicity = 0
		for b in board_combined:
			nonzero = b[b != 0]
			if len(nonzero) >= 2:
				diffs = np.diff(nonzero)
				monotonicity += all(diffs >= 0) * 2 or all(diffs <= 0)

		smoothness_horizontal = np.abs(np.diff(board))
		smoothness_horizontal[board[:, :-1] * board[:, 1:] == 0] = 0
		smoothness_vertical = np.abs(np.diff(board_t))
		smoothness_vertical[board_t[:, :-1] * board_t[:, 1:] == 0] = 0
		smoothness = - np.sum(smoothness_horizontal) - np.sum(smoothness_vertical)

		return (
			weights[0] * empty +
			weights[1] * merge +
			weights[2] * gradient +
			weights[3] * distribution +
			weights[4] * monotonicity +
			weights[5] * smoothness
		)

	@staticmethod
	def search(board, depth, max_depth, weights):
		if MyMatrixer.lose(board):
			return -1000
		if depth >= max_depth:
			return ExpectimaxAlgorithm.evaluate(board, weights)
		if not depth % 2:
			score = -np.inf
			for movement in MOVEMENT:
				subsequent, _ = MyMatrixer.moving(board, movement)
				if not np.array_equal(board, subsequent):
					score = max(score, ExpectimaxAlgorithm.search(subsequent, depth + 1, max_depth, weights))
			return score
		else:
			empty_cells = tuple(np.argwhere(board == 0))
			if not empty_cells:
				return ExpectimaxAlgorithm.evaluate(board, weights)
			else:
				score = 0
				for empty_cell in empty_cells:
					for tile, prob in {2: 0.9, 4: 0.1}.items():
						subsequent = board.copy()
						subsequent[tuple(empty_cell)] = tile
						score += prob * ExpectimaxAlgorithm.search(subsequent, depth + 1, max_depth, weights)
				return score / len(empty_cells)

	@staticmethod
	#@mu.Decorator.timing
	def infer(board, weights):
		best_score, best_movement = -np.inf, None
		for movement in MOVEMENT:
			subsequent, _ = MyMatrixer.moving(board, movement)
			if not np.array_equal(board, subsequent):
				max_depth = 2 if np.count_nonzero(board == 0) >= 4 else 3
				score = ExpectimaxAlgorithm.search(subsequent, 0, max_depth, weights)
				if score >= best_score:
					best_score, best_movement = score, movement
		return best_movement



class GeneticAlgorithm:
	GENE_SIZE, GENE_COUNT = 4, 6
	GENE_TYPE, DNA_SIZE = 2 ** GENE_SIZE, GENE_SIZE * GENE_COUNT

	POPULATION_SIZE = 80
	POPULATION_PATH = util.join_path(util.RESOURCE, "game2048", "population.pkl")

	ELITE_SIZE, INFERIOR_SIZE = 5, 5
	COMMON_SIZE = POPULATION_SIZE - ELITE_SIZE - INFERIOR_SIZE

	CROSSOVER_RATE = 0.8
	MUTATION_RATE = 0.1

	EXTRA_FIT = 4
	EPOCH = 50

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
	def _fit(epoch, i, j, weights):
		msg = (
			f"EPOCH[{epoch + 1:2}/{GeneticAlgorithm.EPOCH}] "
			f"DNA[{i + 1:2}/{GeneticAlgorithm.POPULATION_SIZE}] "
			f"GAME[{j + 1:2}/{GeneticAlgorithm.EXTRA_FIT + 1}] %s"
		)

		board, step = MyMatrixer.reset(), 0
		while True:
			if MyMatrixer.win(board):
				score = step + np.max(board) * 5 + 100
				print(msg % f"STEP[{step:3}] SCORE[{score:3}]")
				return score, True
			if MyMatrixer.lose(board):
				score = step + np.max(board) * 5
				print(msg % f"STEP[{step:3}] SCORE[{score:3}]")
				return score, False

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
		fitness, reserved = GeneticAlgorithm._fit(epoch, i, 0, weights)
		if reserved:
			for j in range(GeneticAlgorithm.EXTRA_FIT):
				fitness += GeneticAlgorithm._fit(epoch, i, j + 1, weights)
			fitness = fitness / (GeneticAlgorithm.EXTRA_FIT + 1)
		return dna, fitness

	@staticmethod
	@mu.Decorator.timing
	def _evaluate(population, epoch):
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
				crossover_point = random.randint(1, GeneticAlgorithm.DNA_SIZE - 1)
				dna1 = population[i]
				dna2 = population[i + 1]
				population[i] = dna1[:crossover_point] + dna2[crossover_point:]
				population[i + 1] = dna2[:crossover_point] + dna1[crossover_point:]
		return population

	@staticmethod
	def _mutate(population):
		return ["".join(
			("0" if int(locus) else "1") if random.random() < GeneticAlgorithm.MUTATION_RATE else locus
			for locus in population[i]
		) for i in range(len(population))]

	@staticmethod
	def train():
		if os.path.exists(GeneticAlgorithm.POPULATION_PATH):
			population = util.FileIO.read(GeneticAlgorithm.POPULATION_PATH)
		else:
			population = [GeneticAlgorithm._encode_dna() for _ in range(GeneticAlgorithm.POPULATION_SIZE)]

		for epoch in range(GeneticAlgorithm.EPOCH):
			fitnesses = GeneticAlgorithm._evaluate(population, epoch)
			util.FileIO.write(GeneticAlgorithm.POPULATION_PATH, fitnesses)
			print(f"EPOCH:{epoch + 1:2} AVG:{sum(fitnesses.values()) // len(fitnesses):3} {fitnesses}")

			population_elite, population_common = GeneticAlgorithm._select(fitnesses)
			population_crossovered = GeneticAlgorithm._crossover(population_common)
			population_mutated = GeneticAlgorithm._mutate(population_crossovered)
			population_newborn = [GeneticAlgorithm._encode_dna() for _ in range(GeneticAlgorithm.INFERIOR_SIZE)]
			population = population_elite + population_mutated + population_newborn


if __name__ == "__main__":
	if 0:
		app = QApplication(sys.argv)
		my_core = MyCore()
		my_core.setFixedSize(my_core.window().size())
		my_core.show()
		sys.exit(app.exec())
	else:
		pool = Pool(processes=cpu_count())
		try:
			GeneticAlgorithm.train()
		finally:
			pool.close()
