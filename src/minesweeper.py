from minesweeper_ui import Ui_MainWindow
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QSizePolicy
from itertools import product
import random
import sys
import util

_QSS = (
	"QPushButton {font-family: 'Rockwell Extra Bold'; font-size: 20px; font-weight: bold; icon-size: 20px}"
	"QPushButton {border-radius: 5px; border: 1px solid %s; background-color: %s}"
)
QSS_UNEXPLORED = _QSS % ("black", "rgb(100,150,200)") + "QPushButton:hover {background-color: rgb(70,120,170)}"
QSS_EXPLORED = _QSS % ("rgb(127,127,127)", "rgb(210,210,210)") + "QPushButton {color: %s}"
QSS_HINT = _QSS % ("black", "rgb(40,90,140)")

DIFFICULTY = {"easy": (9, 9, 10), "medium": (16, 16, 40), "hard": (16, 30, 99)}
COLOR = {
	1: "rgb(045,015,255)", 2: "rgb(034,127,000)", 3: "rgb(243,018,022)", 4: "rgb(018,003,129)",
	5: "rgb(122,004,006)", 6: "rgb(041,128,129)", 7: "rgb(000,000,000)", 8: "rgb(124,124,124)"
}

APP = QApplication([])
SCREEN_SIZE = APP.primaryScreen().size().width(), APP.primaryScreen().size().height()
BLOCK_SIZE = 35


class MyCore(QMainWindow, Ui_MainWindow):
	row_count, col_count, mine_count = None, None, None
	minefield, amount_pressed, amount_flagged = None, None, None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../minesweeper/minesweeper"))

		self.radioButton_easy.clicked.connect(self.switch)
		self.radioButton_medium.clicked.connect(self.switch)
		self.radioButton_hard.clicked.connect(self.switch)

		self.timer = QTimer()
		self.timer.setInterval(10)
		util.cast(self.timer).timeout.connect(lambda: MyStatic.timeout(self))

		rc, cc, _ = DIFFICULTY["hard"]
		for i, j in product(range(rc), range(cc)):
			widget = MineBlock(i, j)
			widget.func_sweep = lambda x=i, y=j: self.func_sweep(x, y)
			widget.func_flag = lambda w=widget: self.func_flag(w)
			widget.func_hint = lambda x=i, y=j: self.func_hint(x, y)
			self.gridLayout.addWidget(widget, i, j)
		self.radioButton_easy.click()

	def switch(self):
		difficulty = self.sender().objectName().split("_")[-1]
		self.row_count, self.col_count, self.mine_count = DIFFICULTY[difficulty]
		row_max, col_max, _ = DIFFICULTY["hard"]
		row_min, col_min, _ = DIFFICULTY["easy"]

		for i, j in product(range(row_max), range(col_max)):
			if i < row_min and j < col_min:
				continue
			self.gridLayout.itemAtPosition(i, j).widget().hide()

		for i, j in product(range(row_max), range(col_max)):
			if i < row_min and j < col_min:
				continue
			if i >= self.row_count or j >= self.col_count:
				continue
			self.gridLayout.itemAtPosition(i, j).widget().show()

		window_size = self.col_count * (BLOCK_SIZE + 1) + 17, self.row_count * (BLOCK_SIZE + 1) + 54
		self.window().setFixedSize(*window_size)
		window_pos = (SCREEN_SIZE[0] - self.window().width()) // 2, (SCREEN_SIZE[1] - self.window().height()) // 2
		self.window().move(*window_pos)
		self.restart()

	def restart(self):
		self.amount_pressed = 0
		self.amount_flagged = 0

		self.timer.stop()
		self.timer.setProperty("time", 0)

		for i, j in product(range(self.row_count), range(self.col_count)):
			widget = self.gridLayout.itemAtPosition(i, j).widget()
			widget.setText("")
			widget.status_pressed = False
			widget.status_flagged = False
			widget.setIcon(QIcon())
			widget.setStyleSheet(QSS_UNEXPLORED)
		MyStatic.message(self)

	def func_sweep(self, x, y):
		if self.minefield[x][y] == 9:
			return self.judge(False)
		self.expand(x, y)
		MyStatic.message(self)

		if self.amount_pressed == self.row_count * self.col_count - self.mine_count:
			return self.judge(True)

	def func_flag(self, w):
		w.status_flagged = not w.status_flagged
		w.setIcon(util.icon("../minesweeper/flag") if w.status_flagged else QIcon())
		self.amount_flagged += 1 if w.status_flagged else -1
		MyStatic.message(self)

	def func_hint(self, x, y):
		if not self.minefield[x][y]:
			return

		flagged_amount = 0
		unflagged_pos = []

		for pos in MyStatic.around(x, y):
			widget = self.gridLayout.itemAtPosition(pos[0], pos[1]).widget()
			if widget.status_pressed:
				continue
			if widget.status_flagged:
				flagged_amount += 1
			else:
				unflagged_pos.append(pos)

		if flagged_amount == self.minefield[x][y]:
			for pos in unflagged_pos:
				if self.amount_pressed:
					self.func_sweep(pos[0], pos[1])
		else:
			for pos in unflagged_pos:
				self.gridLayout.itemAtPosition(pos[0], pos[1]).widget().setStyleSheet(QSS_HINT)
			self.gridLayout.itemAtPosition(x, y).widget().hint_pos = unflagged_pos

	def expand(self, x, y):
		if self.minefield[x][y] == 9:
			return self.judge(False)
		if not MyStatic.is_valid_pos(x, y):
			return

		widget = self.gridLayout.itemAtPosition(x, y).widget()
		if widget.status_pressed:
			return
		if widget.status_flagged:
			return

		mine_value = self.minefield[x][y]
		widget.status_pressed = True
		widget.setText(str(mine_value).strip("0"))
		widget.setStyleSheet(QSS_EXPLORED % COLOR.get(mine_value, "black"))
		self.amount_pressed += 1

		if not mine_value:
			for pos in MyStatic.around(x, y):
				self.expand(pos[0], pos[1])

	def judge(self, win):
		for i, j in product(range(self.row_count), range(self.col_count)):
			widget = self.gridLayout.itemAtPosition(i, j).widget()
			if self.minefield[i][j] == 9 and not widget.status_flagged:
				if win:
					widget.setIcon(util.icon("../minesweeper/flag"))
				else:
					widget.setIcon(util.icon("../minesweeper/mine"))
			elif self.minefield[i][j] != 9 and widget.status_flagged:
				widget.setIcon(util.icon("../minesweeper/misjudged"))

		self.timer.stop()
		self.amount_flagged = self.mine_count
		MyStatic.message(self)
		util.dialog("You won", "success") if win else util.dialog("You lose", "error")
		self.restart()

	def leaveEvent(self, a0):
		super().leaveEvent(a0)
		if self.amount_pressed and self.timer.isActive():
			self.timer.stop()

	def enterEvent(self, event):
		super().enterEvent(event)
		if self.amount_pressed and not self.timer.isActive():
			self.timer.start()

class MyStatic:
	@staticmethod
	def reset(x, y):
		mine_poses = [(i, j) for i, j in product(range(my_core.row_count), range(my_core.col_count))]
		for i, j in product(range(-2, 3), repeat=2):
			if MyStatic.is_valid_pos(x + i, y + j):
				mine_poses.remove((x + i, y + j))
		mine_poses = random.sample(mine_poses, my_core.mine_count)

		my_core.minefield = [[((i, j) in mine_poses) * 9 for j in range(my_core.col_count)] for i in range(my_core.row_count)]
		for mine_pos in mine_poses:
			for i, j in MyStatic.around(mine_pos[0], mine_pos[1]):
				if my_core.minefield[i][j] != 9:
					my_core.minefield[i][j] += 1

	@staticmethod
	def is_valid_pos(x, y):
		return 0 <= x < my_core.row_count and 0 <= y < my_core.col_count

	@staticmethod
	def around(x, y):
		return [(x + i, y + j) for i, j in product(range(-1, 2), repeat=2) if MyStatic.is_valid_pos(x + i, y + j) and (i or j)]

	@staticmethod
	def message(self):
		rest = self.mine_count - self.amount_flagged
		cost = round(self.timer.property("time"))
		self.statusbar.showMessage(f"剩余: {rest:02}  用时: {cost:03}")

	@staticmethod
	def timeout(self):
		self.timer.setProperty("time", self.timer.property("time") + self.timer.interval() / 1000)
		if self.timer.property("time") >= 999:
			self.timer.stop()
		MyStatic.message(self)


class MineBlock(QPushButton):
	func_sweep, func_flag, func_hint = None, None, None
	status_pressed, status_flagged = None, None
	hint_pos = []

	def __init__(self, x, y):
		super().__init__()
		self.setMinimumSize(BLOCK_SIZE, BLOCK_SIZE)
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.x, self.y = x, y

	def mousePressEvent(self, e):
		super().mousePressEvent(e)
		if e.buttons() == Qt.MouseButton.LeftButton and not self.status_flagged:
			if not my_core.amount_pressed:
				my_core.timer.start()
				MyStatic.reset(self.x, self.y)
			if not self.status_pressed:
				self.func_sweep()
			else:
				self.func_hint()
		elif e.buttons() == Qt.MouseButton.RightButton:
			if not self.status_pressed:
				self.func_flag()
			else:
				self.func_hint()

	def mouseReleaseEvent(self, e):
		for pos in self.hint_pos:
			my_core.gridLayout.itemAtPosition(pos[0], pos[1]).widget().setStyleSheet(QSS_UNEXPLORED)
		self.hint_pos.clear()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
