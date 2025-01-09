from greedy_snake_ui import Ui_MainWindow
from PyQt6.QtCore import QRect, QTimer, Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import product
import random
import sys
import util

ROW_COUNT, COL_COUNT, BLOCK_SIZE = 30, 30, 20
PIXMAP_SIZE = COL_COUNT * BLOCK_SIZE, ROW_COUNT * BLOCK_SIZE
WINDOW_SIZE = PIXMAP_SIZE[0] + 18, PIXMAP_SIZE[1] + 20
DIRECTION = {Qt.Key.Key_Up: (-1, 0), Qt.Key.Key_Down: (1, 0), Qt.Key.Key_Left: (0, -1), Qt.Key.Key_Right: (0, 1)}


class MyCore(QMainWindow, Ui_MainWindow):
	direction, field, score = None, None, None
	snake, food, cut = None, None, None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../greedy_snake/snake"))

		self.timer = QTimer()
		self.timer.setInterval(200)
		util.cast(self.timer).timeout.connect(self.timeout)
		
		self.label.setPixmap(QPixmap(*PIXMAP_SIZE))
		self.restart()

	def restart(self):
		self.score = 0
		self.direction = random.choice(list(DIRECTION.values()))
		self.snake = [(ROW_COUNT // 2 + i * self.direction[0], COL_COUNT // 2 + i * self.direction[1]) for i in range(3)]
		self.field = [(i, j) for i, j in product(range(ROW_COUNT), range(COL_COUNT)) if (i, j) not in self.snake]
		self.food = random.choice(self.field)
		self.draw()

	def timeout(self):
		head = self.snake[-1][0] + self.direction[0], self.snake[-1][1] + self.direction[1]
		if head in self.snake or not 0 <= head[0] < ROW_COUNT or not 0 <= head[1] < COL_COUNT:
			util.dialog("Game over", "error")
			return self.restart()

		self.snake.append(head)
		self.field.remove(head)
		if head == self.food:
			self.score += 1
			if random.random() < 0.2 and len(self.snake) >= 5 and not self.cut:
				self.food, self.cut = random.sample(self.field, 2)
			else:
				self.food = random.choice(self.field)
		elif head == self.cut:
			self.score += 2
			self.cut = None
			for _ in range(3):
				self.field.append(self.snake.pop(0))
		else:
			self.field.append(self.snake.pop(0))
		self.draw()

	def keyPressEvent(self, a0):
		if not self.timer.isActive():
			return
		if a0.key() not in DIRECTION:
			return

		direct = DIRECTION[util.cast(a0.key())]
		if self.direction[0] != direct[0] and self.direction[1] != direct[1]:
			self.direction = direct
			self.timeout()
			self.timer.start()

	def draw(self):
		pixmap = self.label.pixmap()
		pixmap.fill(Qt.GlobalColor.black)
		with QPainter(pixmap) as painter:
			painter.setPen(Qt.PenStyle.NoPen)
			if self.cut:
				painter.setBrush(Qt.GlobalColor.blue)
				painter.drawRect(QRect(self.cut[1] * BLOCK_SIZE, self.cut[0] * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
			if self.food:
				painter.setBrush(Qt.GlobalColor.red)
				painter.drawRect(QRect(self.food[1] * BLOCK_SIZE, self.food[0] * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
			for s in self.snake:
				painter.setBrush(Qt.GlobalColor.white)
				painter.drawRect(QRect(s[1] * BLOCK_SIZE, s[0] * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
		self.label.setPixmap(pixmap)
		self.statusbar.showMessage(f"当前得分: {self.score}")

	def leaveEvent(self, a0):
		super().leaveEvent(a0)
		if self.timer.isActive():
			self.timer.stop()

	def enterEvent(self, event):
		super().enterEvent(event)
		if not self.timer.isActive():
			self.timer.start()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(*WINDOW_SIZE)
	my_core.show()
	sys.exit(app.exec())
