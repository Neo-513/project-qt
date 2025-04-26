from greedysnake_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import product
import random
import sys
import util


class MyCore(QMainWindow, Ui_MainWindow):
	WILDERNESS = {(i, j) for i, j in product(range(20), repeat=2)}
	POSITION = {(i, j): (j * 25 + 50, i * 25 + 50, 25, 25) for i, j in product(range(20), repeat=2)}
	DIRECTION = {Qt.Key.Key_Up: (-1, 0), Qt.Key.Key_Down: (1, 0), Qt.Key.Key_Left: (0, -1), Qt.Key.Key_Right: (0, 1)}
	LARVA = {d: [[(x - i * d[0], y - i * d[1]) for i in range(3)] for x, y in product([9, 10], repeat=2)] for d in DIRECTION.values()}

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../greedysnake/logo"))

		self.label_theme1 = util.mask(self.label_canvas, (9, 0), "../greedysnake/theme1")
		self.label_theme2 = util.mask(self.label_canvas, (9, 0), "../greedysnake/theme2", hide=True)
		self.label_scoreboard = util.mask(self.label_canvas, (9, 0), "../greedysnake/scoreboard")
		self.label_pause = util.mask(self.label_canvas, (9, 0), QColor(255, 255, 255, 80), hide=True)
		util.pixmap(self.label_canvas, color=Qt.GlobalColor.black)

		self.direction = self.snake = self.food = None
		self.timer = util.timer(200, self.timeout)
		self.restart()

	def restart(self):
		self.direction = random.choice(list(self.DIRECTION.values()))
		self.snake = random.choice(self.LARVA[self.direction]).copy()
		self.food = random.choice(list(self.WILDERNESS - set(self.snake)))

		self.timer.start()
		self.timeout()

	def mousePressEvent(self, a0):
		if a0.button() == Qt.MouseButton.RightButton:
			self.label_theme1.setHidden(not self.label_theme1.isHidden())
			self.label_theme2.setHidden(not self.label_theme2.isHidden())

	def keyPressEvent(self, event):
		if event.key() == Qt.Key.Key_Space:
			if self.timer.isActive():
				self.timer.stop()
				return self.label_pause.show()
			else:
				self.timer.start()
				return self.label_pause.hide()

		if not self.timer.isActive():
			return
		if event.key() == Qt.Key.Key_Return:
			self.timer.stop()
			return self.restart()

		if event.key() in self.DIRECTION:
			direction = self.DIRECTION[event.key()]
			if self.direction[0] != direction[0] and self.direction[1] != direction[1]:
				self.direction = direction
				self.timer.start()
				self.timeout()

	def timeout(self):
		head = self.snake[0][0] + self.direction[0], self.snake[0][1] + self.direction[1]
		if head in self.snake or not 0 <= head[0] < 20 or not 0 <= head[1] < 20:
			util.dialog("Game over", "error")
			return self.restart()

		self.snake.insert(0, head)
		if head == self.food:
			self.food = random.choice(list(self.WILDERNESS - set(self.snake)))
			self.scoring()
		else:
			self.snake.pop()
		self.display()

	def display(self):
		pixmap = self.label_canvas.pixmap()
		pixmap.fill(Qt.GlobalColor.black)
		with QPainter(pixmap) as painter:
			painter.fillRect(*self.POSITION[self.food], Qt.GlobalColor.red)
			offset = int(200 / len(self.snake))
			for i, pos in enumerate(self.snake):
				painter.fillRect(*self.POSITION[pos], QColor(0, 255, 0, 255 - offset * i))
		self.label_canvas.setPixmap(pixmap)

	def scoring(self):
		pixmap = self.label_scoreboard.pixmap()
		pixmap.fill(Qt.GlobalColor.transparent)
		with QPainter(pixmap) as painter:
			painter.setFont(QFont("", 16))
			painter.setPen(Qt.GlobalColor.white)
			painter.drawText(60, 60, 100, 50, Qt.AlignmentFlag.AlignLeft, f"Score {len(self.snake) - 3}")
		self.label_scoreboard.setPixmap(pixmap)


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
