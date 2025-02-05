from game2048_ui import Ui_MainWindow
from PyQt6.QtCore import QRect, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import product
import random
import sys
import util

FRAME = 10
FONT = QFont(QFont().family(), 40, QFont.Weight.Bold)

GROOVE_SIZE, GAP_SIZE = 100, 15
GROOVE = {(i, j): (j * (GROOVE_SIZE + GAP_SIZE) + GAP_SIZE, i * (GROOVE_SIZE + GAP_SIZE) + GAP_SIZE) for i, j in product(range(4), repeat=2)}
CANVAS_SIZE = GROOVE_SIZE * 4 + GAP_SIZE * 5
WINDOW_SIZE = CANVAS_SIZE + 18, CANVAS_SIZE + 20

COLOR_SKELETON = QColor(187, 173, 160)
COLOR_NUM = QColor(118, 110, 101)
COLOR = {
	0: QColor(205, 193, 180), 2: QColor(238, 228, 218), 4: QColor(237, 224, 200), 8: QColor(242, 177, 121),
	16: QColor(245, 149, 99), 32: QColor(246, 124, 95), 64: QColor(246, 94, 59), 128: QColor(237, 207, 114),
	256: QColor(237, 204, 97), 512: QColor(228, 192, 42), 1024: QColor(226, 186, 19), 2048: QColor(236, 196, 0)
}

ROTATE = {
	Qt.Key.Key_Left: (lambda m: m, lambda m: m),
	Qt.Key.Key_Right: (lambda m: [row[::-1] for row in m][::-1], lambda m: [row[::-1] for row in m][::-1]),
	Qt.Key.Key_Up: (lambda m: [list(col) for col in zip(*m)][::-1], lambda m: [list(col[::-1]) for col in zip(*m)]),
	Qt.Key.Key_Down: (lambda m: [list(col[::-1]) for col in zip(*m)], lambda m: [list(col) for col in zip(*m)][::-1])
}
TRANS = {
	Qt.Key.Key_Left: lambda x, y: (x, y),
	Qt.Key.Key_Right: lambda x, y: (3 - x, 3 - y),
	Qt.Key.Key_Up: lambda x, y: (y, 3 - x),
	Qt.Key.Key_Down: lambda x, y: (3 - y, x)
}


class MyCore(QMainWindow, Ui_MainWindow):
	field, skeleton, trails = None, None, None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../game2048/2048"))

		self.timer = QTimer()
		self.timer.setInterval(15)
		util.cast(self.timer).timeout.connect(self.draw)

		self.skeleton = QPixmap(CANVAS_SIZE, CANVAS_SIZE)
		self.skeleton.fill(COLOR_SKELETON)
		with QPainter(self.skeleton) as skeleton_painter:
			skeleton_painter.setPen(Qt.PenStyle.NoPen)
			skeleton_painter.setBrush(COLOR[0])
			for skeleton_rect in GROOVE.values():
				skeleton_painter.drawRect(QRect(*skeleton_rect, GROOVE_SIZE, GROOVE_SIZE))
		self.label.setPixmap(self.skeleton)
		self.statusbar.showMessage("按 Enter 重新开始")
		self.restart()

	def restart(self):
		self.field = [[0] * 4 for _ in range(4)]
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
		self.field = ROTATE[util.cast(a0.key())][0](self.field)
		self.merge(TRANS[util.cast(a0.key())])
		self.field = ROTATE[util.cast(a0.key())][1](self.field)

		self.timer.setProperty("frame", 0)
		self.timer.start()

		for i, j in product(range(4), repeat=2):
			if self.field[i][j] == 2048:
				util.dialog("You won", "success")
				return self.restart()

		if self.field != previous:
			self.add(random.choice((2, 4)))

		for i, j in product(range(4), repeat=2):
			if not self.field[i][j]:
				return
			if i and self.field[i][j] == self.field[i - 1][j]:
				return
			if j and self.field[i][j] == self.field[i][j - 1]:
				return

		util.dialog("You lose", "error")
		self.restart()

	def add(self, num):
		x, y = random.choice([(i, j) for i, j in product(range(4), repeat=2) if not self.field[i][j]])
		self.field[x][y] = num

	def merge(self, trans):
		following, merged, self.trails = [], [], []
		for i in range(4):
			following.append([])
			merged.append(False)
			if self.field[i][0]:
				following[i].append(self.field[i][0])
				self.trails.append([trans(i, 0), trans(i, 0), self.field[i][0]])

		for j, i in product(range(1, 4), range(4)):
			num = self.field[i][j]
			if not num:
				continue
			if following[i] and following[i][-1] == num and not merged[i]:
				following[i][-1] *= 2
				merged[i] = True
			else:
				following[i].append(num)
				merged[i] = False
			self.trails.insert(0, [trans(i, j), trans(i, len(following[i]) - 1), num])
		self.field = [f + [0] * (4 - len(f)) for f in following]

	def display(self):
		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(FONT)
			for (i, j), g in GROOVE.items():
				num, rect = self.field[i][j], QRect(*g, GROOVE_SIZE, GROOVE_SIZE)
				painter.setPen(Qt.PenStyle.NoPen)
				painter.setBrush(COLOR[num])
				painter.drawRect(rect)
				painter.setPen(COLOR_NUM)
				painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(num).strip("0"))
		self.label.setPixmap(pixmap)

	def draw(self):
		self.timer.setProperty("frame", self.timer.property("frame") + 1)
		if self.timer.property("frame") > FRAME:
			self.timer.stop()
			self.display()
			return

		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(FONT)
			for trail in self.trails:
				pos_start, pos_end, num = trail
				groove_start, groove_end = GROOVE[pos_start], GROOVE[pos_end]

				offset_x = (groove_end[0] - groove_start[0]) / FRAME
				offset_y = (groove_end[1] - groove_start[1]) / FRAME
				x = int(groove_start[0] + offset_x * self.timer.property("frame"))
				y = int(groove_start[1] + offset_y * self.timer.property("frame"))
				rect = QRect(x, y, GROOVE_SIZE, GROOVE_SIZE)

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
