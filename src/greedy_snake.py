from greedy_snake_ui import Ui_MainWindow
from PyQt6.QtCore import QTimer, Qt, QRect, QSize
from PyQt6.QtGui import QBrush, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import product
import random
import sys
import util

ROW_COUNT, COL_COUNT, BLOCK_SIZE = 30, 30, 20
FIELD_WIDTH, FIELD_HEIGHT = COL_COUNT * BLOCK_SIZE, ROW_COUNT * BLOCK_SIZE
KEY = {Qt.Key.Key_Up: (-1, 0), Qt.Key.Key_Down: (1, 0), Qt.Key.Key_Left: (0, -1), Qt.Key.Key_Right: (0, 1)}


class QtCore(QMainWindow, Ui_MainWindow):
	direction, snake, score = None, None, None
	field, fruit, cut = None, None, None

	TIMER = QTimer()
	TIMER.setInterval(200)

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../greedy_snake/snake"))

		util.cast(self.TIMER).timeout.connect(self.timeout)
		self.label.setPixmap(QPixmap(QSize(FIELD_WIDTH, FIELD_HEIGHT)))
		self.draw([], redraw=True)
		self.restart()

	def restart(self):
		pos_x = ROW_COUNT // 2
		pos_y = COL_COUNT // 2

		self.direction = random.choice(list(KEY.values()))
		self.snake = [(pos_x + i * self.direction[0], pos_y + i * self.direction[1]) for i in range(3)]
		self.score = 0

		self.field = set((i, j) for i, j in product(range(ROW_COUNT), range(COL_COUNT)) if (i, j) not in self.snake)
		self.fruit = random.choice(list(self.field))
		self.draw([(s, Qt.GlobalColor.white) for s in self.snake] + [(self.fruit, Qt.GlobalColor.red)], redraw=True)

	def timeout(self):
		head = self.snake[-1][0] + self.direction[0], self.snake[-1][1] + self.direction[1]
		if head in self.snake or head[0] < 0 or head[0] >= ROW_COUNT or head[1] < 0 or head[1] >= COL_COUNT:
			util.dialog("Game over", "error")
			return self.restart()

		self.snake.append(head)
		self.field.remove(head)
		blocks = [(head, Qt.GlobalColor.white)]

		if head == self.fruit:
			self.score += 1
			if random.random() < 0.2 and len(self.snake) >= 5 and not self.cut:
				self.fruit, self.cut = random.sample(list(self.field), 2)
				blocks.append((self.fruit, Qt.GlobalColor.red))
				blocks.append((self.cut, Qt.GlobalColor.blue))
			else:
				self.fruit = random.choice(list(self.field))
				blocks.append((self.fruit, Qt.GlobalColor.red))
		elif head == self.cut:
			self.score += 2
			self.cut = None
			for _ in range(3):
				tail = self.snake.pop(0)
				self.field.add(tail)
				blocks.append((tail, Qt.GlobalColor.black))
		else:
			tail = self.snake.pop(0)
			self.field.add(tail)
			blocks.append((tail, Qt.GlobalColor.black))

		self.draw(blocks)
		self.statusbar.showMessage(f"当前得分: {self.score}")

	def keyPressEvent(self, a0):
		if not self.TIMER.isActive():
			return
		if a0.key() not in KEY:
			return

		direct = KEY[a0.key()]
		if self.direction[0] != direct[0] and self.direction[1] != direct[1]:
			self.direction = direct
			self.timeout()
			self.TIMER.start()

	def draw(self, blocks, redraw=False):
		pixmap = self.label.pixmap()
		if redraw:
			pixmap.fill(Qt.GlobalColor.black)
		painter = QPainter(pixmap)
		painter.setPen(Qt.PenStyle.NoPen)
		for block in blocks:
			pos, color = block
			painter.setBrush(QBrush(color))
			painter.drawRect(QRect(pos[1] * BLOCK_SIZE, pos[0] * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
		painter.end()
		self.label.setPixmap(pixmap)

	def leaveEvent(self, a0):
		super().leaveEvent(a0)
		if self.TIMER.isActive():
			self.TIMER.stop()

	def enterEvent(self, event):
		super().enterEvent(event)
		if not self.TIMER.isActive():
			self.TIMER.start()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	qt_core = QtCore()
	qt_core.setFixedSize(FIELD_WIDTH + 18, FIELD_HEIGHT + 20)
	qt_core.show()
	sys.exit(app.exec())
