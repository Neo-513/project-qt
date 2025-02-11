from game2048_ui import Ui_MainWindow
from PyQt6.QtCore import pyqtSignal, QRect, QThread, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import product
from multiprocessing import Pool, cpu_count
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
	[6, 5, 4, 3],
	[5, 4, 3, 2],
	[4, 3, 2, 1],
	[3, 2, 1, 0]
])


class MyCore(QMainWindow, Ui_MainWindow):
	board = np.zeros((4, 4), dtype=int)
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
		movement = ExpectimaxAlgorithm.infer(self.board)
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
	def reset(board):
		board.fill(0)
		MyMatrixer.add(board)
		MyMatrixer.add(board)

	@staticmethod
	def add(board):
		empty_cells = tuple(np.argwhere(board == 0))
		empty_pos = tuple(random.choice(empty_cells))
		board[empty_pos] = 1 if random.random() < 0.9 else 2

	@staticmethod
	def win(board):
		return 2048 in board

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
		movement = ExpectimaxAlgorithm.infer(my_core.board)
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
	weights = (5, 10, 0.2, 2, 2, 2)

	@staticmethod
	def evaluate(board):
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
			ExpectimaxAlgorithm.weights[0] * empty +
			ExpectimaxAlgorithm.weights[1] * merge +
			ExpectimaxAlgorithm.weights[2] * gradient +
			ExpectimaxAlgorithm.weights[3] * distribution +
			ExpectimaxAlgorithm.weights[4] * monotonicity +
			ExpectimaxAlgorithm.weights[5] * smoothness
		)

	@staticmethod
	def search_deeply(board, depth, max_depth):
		if MyMatrixer.lose(board):
			return -1000
		if depth >= max_depth:
			return ExpectimaxAlgorithm.evaluate(board)
		if not depth % 2:
			score = -np.inf
			for movement in MOVEMENT:
				subsequent, _ = MyMatrixer.moving(board, movement)
				if not np.array_equal(board, subsequent):
					score = max(score, ExpectimaxAlgorithm.search_deeply(subsequent, depth + 1, max_depth))
			return score
		else:
			empty_cells = tuple(np.argwhere(board == 0))
			if not empty_cells:
				return ExpectimaxAlgorithm.evaluate(board)
			else:
				score = 0
				for empty_cell in empty_cells:
					for tile, prob in {2: 0.9, 4: 0.1}.items():
						subsequent = board.copy()
						subsequent[tuple(empty_cell)] = tile
						score += prob * ExpectimaxAlgorithm.search_deeply(subsequent, depth + 1, max_depth)
				return score / len(empty_cells)

	@staticmethod
	def search(board, movement):
		subsequent, _ = MyMatrixer.moving(board, movement)
		if not np.array_equal(board, subsequent):
			max_depth = 3 if np.count_nonzero(board == 0) < 5 else 2
			score = ExpectimaxAlgorithm.search_deeply(subsequent, 0, max_depth)
			return score, movement
		return -np.inf, None

	@staticmethod
	#@mu.Decorator.timing
	def infer(board):
		global pool
		results = pool.starmap(ExpectimaxAlgorithm.search, [(board, movement) for movement in MOVEMENT])
		best_score, best_movement = -np.inf, None
		for score, movement in results:
			if score >= best_score:
				best_score, best_movement = score, movement
		return best_movement


class GeneticAlgorithm:
	POPULATION_AMOUNT = 50
	WEIGHT_AMOUNT = 6
	GENE_SIZE = 4

	CROSSOVER_RATE = 0.8
	MUTATION_RATE = 0.05
	EPOCH = 100

	board = np.zeros((4, 4), dtype=int)
	scores = None

	@staticmethod
	def weigh(gene):
		return tuple(int(gene[i * GeneticAlgorithm.GENE_SIZE:(i + 1) * GeneticAlgorithm.GENE_SIZE], 2) for i in range(GeneticAlgorithm.WEIGHT_AMOUNT))

	@staticmethod
	def population():
		return ["".join(f"{bin(random.randint(0, 15))[2:]:>0{GeneticAlgorithm.GENE_SIZE}}" for _ in range(GeneticAlgorithm.WEIGHT_AMOUNT)) for _ in range(GeneticAlgorithm.POPULATION_AMOUNT)]

	@staticmethod
	def crossover(genes):
		for i in range(0, len(genes), 2):
			if random.random() >= GeneticAlgorithm.CROSSOVER_RATE:
				continue
			crossover_point = random.randint(1, len(genes[i]) - 2)
			parents = genes[i], genes[i + 1]
			genes[i] = parents[0][:crossover_point] + parents[1][crossover_point:]
			genes[i + 1] = parents[1][:crossover_point] + parents[0][crossover_point:]
		return genes

	@staticmethod
	def mutation(genes):
		for i, gene in enumerate(genes):
			if random.random() >= GeneticAlgorithm.MUTATION_RATE:
				continue
			gn = list(gene)
			for _ in range(random.randint(1, 5)):
				crossover_point = random.randint(0, len(gene) - 1)
				gn[crossover_point] = "0" if gn[crossover_point] else "1"
			genes[i] = "".join(gn)
		return genes

	@staticmethod
	def evaluate(genes, epoch):
		scores = {}
		for i, gene in enumerate(genes):
			ExpectimaxAlgorithm.weights = GeneticAlgorithm.weigh(gene)
			MyMatrixer.reset(GeneticAlgorithm.board)
			score = 0

			while True:
				if MyMatrixer.win(GeneticAlgorithm.board):
					scores[gene] = score + np.max(GeneticAlgorithm.board) * 10 + 100
					win = True
					break
				if MyMatrixer.lose(GeneticAlgorithm.board):
					scores[gene] = score + np.max(GeneticAlgorithm.board) * 10
					win = False
					break

				movement = ExpectimaxAlgorithm.infer(GeneticAlgorithm.board)
				previous = GeneticAlgorithm.board.copy()
				GeneticAlgorithm.board, _ = MyMatrixer.moving(GeneticAlgorithm.board, movement)

				if not np.array_equal(GeneticAlgorithm.board, previous):
					MyMatrixer.add(GeneticAlgorithm.board)
				score += 1

			if 0 in ExpectimaxAlgorithm.weights:
				scores[gene] *= 0.8
			print(f"[EPOCH {epoch + 1:3}/{GeneticAlgorithm.EPOCH}][GENE {i + 1:3}/{len(genes)}][STEP {score:3}] SCORE: {scores[gene]} ({'WIN' if win else 'LOSE'})")
		return scores

	@staticmethod
	def eliminate(scores):
		scores = {gene: score for gene, score in scores.items() if score}
		if not scores:
			return []
		reserved_scores = sorted(list(scores.values()), reverse=True)
		eliminated_scores = reserved_scores[:int(len(reserved_scores) * 0.8)]
		return [gene for gene, score in scores.items() if score in eliminated_scores]

	@staticmethod
	def complement(old_genes, new_genes):
		amount = GeneticAlgorithm.POPULATION_AMOUNT - len(old_genes)
		return old_genes + random.sample(new_genes, amount)

	@staticmethod
	def train():
		reserved_genes = GeneticAlgorithm.population()
		for epoch in range(GeneticAlgorithm.EPOCH):
			crossovered_genes = GeneticAlgorithm.crossover(reserved_genes)
			mutated_genes = GeneticAlgorithm.mutation(crossovered_genes)
			scores = GeneticAlgorithm.evaluate(mutated_genes, epoch)
			eliminate_genes = GeneticAlgorithm.eliminate(scores)
			reserved_genes = GeneticAlgorithm.complement(eliminate_genes, mutated_genes)
			print({GeneticAlgorithm.weigh(gene): scores[gene] for gene in reserved_genes})


if __name__ == "__main__":
	pool = Pool(processes=cpu_count())
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	#my_core.show()
	GeneticAlgorithm.train()
	sys.exit(app.exec())
