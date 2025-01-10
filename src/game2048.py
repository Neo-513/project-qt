from game2048_ui import Ui_MainWindow
from PyQt6.QtCore import QRect, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import product
import numpy as np
import random
import sys
import util

SIDE_COUNT, GROOVE_SIDE, GAP = 4, 100, 15
PIXMAP_SIDE = SIDE_COUNT * (GROOVE_SIDE + GAP) + GAP
WINDOW_SIZE = PIXMAP_SIDE + 18, PIXMAP_SIDE + 20

INTERVAL, FREQUENCY = 15, 10
FONT = QFont(QFont().family(), 40, QFont.Weight.Bold)
GROOVE = {(i, j): (j * (GROOVE_SIDE + GAP) + GAP, i * (GROOVE_SIDE + GAP) + GAP) for i, j in product(range(SIDE_COUNT), range(SIDE_COUNT))}

COLOR_SKELETON = QColor(187, 173, 160)
COLOR_NUM = QColor(118, 110, 101)
COLOR = {
	0: QColor(205, 193, 180), 2: QColor(238, 228, 218), 4: QColor(237, 224, 200), 8: QColor(242, 177, 121),
	16: QColor(245, 149, 99), 32: QColor(246, 124, 95), 64: QColor(246, 94, 59), 128: QColor(237, 207, 114),
	256: QColor(237, 204, 97), 512: QColor(228, 192, 42), 1024: QColor(226, 186, 19), 2048: QColor(236, 196, 0)
}

ROTATE = {Qt.Key.Key_Left: 0, Qt.Key.Key_Right: 2, Qt.Key.Key_Up: 1, Qt.Key.Key_Down: -1}
TRANSFORMATION = {
	0: {(i, j): (i, j) for i, j in product(range(SIDE_COUNT), range(SIDE_COUNT))},
	2: {(i, j): (SIDE_COUNT - 1 - i, SIDE_COUNT - 1 - j) for i, j in product(range(SIDE_COUNT), range(SIDE_COUNT))},
	1: {(i, j): (j, SIDE_COUNT - 1 - i) for i, j in product(range(SIDE_COUNT), range(SIDE_COUNT))},
	-1: {(i, j): (SIDE_COUNT - 1 - j, i) for i, j in product(range(SIDE_COUNT), range(SIDE_COUNT))}
}


class MyCore(QMainWindow, Ui_MainWindow):
	field, skeleton = np.zeros((SIDE_COUNT, SIDE_COUNT), dtype=int), None
	trails, trans = None, None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../game2048/2048"))

		self.timer = QTimer()
		self.timer.setInterval(INTERVAL)
		util.cast(self.timer).timeout.connect(self.draw)
		
		self.skeleton = QPixmap(PIXMAP_SIDE, PIXMAP_SIDE)
		self.skeleton.fill(COLOR_SKELETON)
		with QPainter(self.skeleton) as painter:
			painter.setPen(Qt.PenStyle.NoPen)
			painter.setBrush(COLOR[0])
			for rect in GROOVE.values():
				painter.drawRect(QRect(*rect, GROOVE_SIDE, GROOVE_SIDE))
		self.label.setPixmap(self.skeleton)

		self.statusbar.showMessage("按 Enter 重新开始")
		self.restart()

	def restart(self):
		self.field.fill(0)
		self.add(2)
		self.add(2)
		self.display()

	def keyPressEvent(self, a0):
		if self.timer.isActive():
			return
		if a0.key() == Qt.Key.Key_Return:
			return self.restart()
		if a0.key() not in ROTATE:
			return

		previous = self.field.copy()
		rotate = ROTATE[util.cast(a0.key())]
		self.trans = TRANSFORMATION[rotate]

		self.field = np.rot90(np.array(self.field), rotate)
		self.merge()
		self.field = np.rot90(np.array(self.field), -rotate)

		self.timer.setProperty("time", 0)
		self.timer.start()

		if np.isin(self.field, 4096).any():
			util.dialog("You won", "success")
			return self.restart()

		if self.field.tolist() != previous.tolist():
			self.add(random.choice((2, 4)))

		for i, j in product(range(SIDE_COUNT), range(SIDE_COUNT)):
			if i and self.field[i][j] == self.field[i - 1][j]:
				return
			if j and self.field[i][j] == self.field[i][j - 1]:
				return

		if not np.isin(self.field, 0).any():
			util.dialog("You lose", "error")
			return self.restart()

	def add(self, num):
		x, y = random.choice([(i, j) for i, j in product(range(SIDE_COUNT), range(SIDE_COUNT)) if not self.field[i][j]])
		self.field[x][y] = num

	def merge(self):
		following, merged, self.trails = [], [], []
		for i in range(SIDE_COUNT):
			following.append([])
			merged.append(False)
			if self.field[i][0]:
				following[i].append(self.field[i][0])
				self.trails.append([self.trans[i, 0], self.trans[i, 0], self.field[i][0]])

		for j, i in product(range(1, SIDE_COUNT), range(SIDE_COUNT)):
			num = self.field[i][j]
			if not num:
				continue
			if following[i] and following[i][-1] == num and not merged[i]:
				following[i][-1] *= 2
				merged[i] = True
			else:
				following[i].append(num)
				merged[i] = False
			self.trails.insert(0, [self.trans[i, j], self.trans[i, len(following[i]) - 1], num])
		self.field = [f + [0] * (SIDE_COUNT - len(f)) for f in following]

	def display(self):
		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(FONT)
			for (i, j), g in GROOVE.items():
				num, rect = self.field[i][j], QRect(*g, GROOVE_SIDE, GROOVE_SIDE)
				painter.setPen(Qt.PenStyle.NoPen)
				painter.setBrush(COLOR[num])
				painter.drawRect(rect)
				painter.setPen(COLOR_NUM)
				painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(num).strip("0"))
		self.label.setPixmap(pixmap)

	def draw(self):
		self.timer.setProperty("time", self.timer.property("time") + 1)
		if self.timer.property("time") > FREQUENCY:
			self.timer.stop()
			self.display()
			return

		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(FONT)
			for trail in self.trails:
				pos_start, pos_end, num = trail
				groove_start, groove_end = GROOVE[pos_start], GROOVE[pos_end]

				offset_x = (groove_end[0] - groove_start[0]) / FREQUENCY
				offset_y = (groove_end[1] - groove_start[1]) / FREQUENCY
				x = int(groove_start[0] + offset_x * self.timer.property("time"))
				y = int(groove_start[1] + offset_y * self.timer.property("time"))
				rect = QRect(x, y, GROOVE_SIDE, GROOVE_SIDE)

				painter.setPen(Qt.PenStyle.NoPen)
				painter.setBrush(COLOR[num])
				painter.drawRect(rect)
				painter.setPen(COLOR_NUM)
				painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(num).strip("0"))
		self.label.setPixmap(pixmap)


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(*WINDOW_SIZE)
	my_core.show()
	sys.exit(app.exec())
