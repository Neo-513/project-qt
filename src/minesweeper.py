from minesweeper_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
from itertools import product
import numpy as np
import os
import random
import sys
import util

PATH = {
	"surrounding": util.join_path(util.RESOURCE, "minesweeper", "surrounding.pkl"),
	"platform": util.join_path(util.RESOURCE, "minesweeper", "platform.pkl")
}
CACHE = {
	"surrounding": util.read(PATH["surrounding"]) if os.path.exists(PATH["surrounding"]) else None,
	"platform": util.read(PATH["platform"]) if os.path.exists(PATH["platform"]) else None
}


class MyCore(QMainWindow, Ui_MainWindow):
	SIZE = {"block": 35, "gap": 1}
	MESSAGE = "剩余: %s  计时: %s"
	DIFFICULTY = {"easy": (9, 9, 10), "medium": (16, 16, 40), "hard": (16, 30, 99)}
	COLOR = (
		"black",
		"rgb(045,015,255)", "rgb(034,127,000)", "rgb(243,018,022)", "rgb(018,003,129)",
		"rgb(122,004,006)", "rgb(041,128,129)", "rgb(000,000,000)", "rgb(124,124,124)"
	)

	_QSS = "QPushButton {icon-size: 20px; border-radius: 5px; border: 1px solid %s; background-color: %s}"
	QSS = {
		"unexplored": _QSS % ("black", "rgb(100, 150, 200)") + "QPushButton:hover {background-color: rgb(70, 120, 170)}",
		"explored": _QSS % ("rgb(127, 127, 127)", "rgb(210, 210, 210)") + "QPushButton {color: %s}",
		"hint": _QSS % ("black", "rgb(40, 90, 140)")
	}

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../minesweeper/logo"))

		self.radioButton_easy.clicked.connect(lambda: self.switch("easy"))
		self.radioButton_medium.clicked.connect(lambda: self.switch("medium"))
		self.radioButton_hard.clicked.connect(lambda: self.switch("hard"))

		r, c, _ = self.DIFFICULTY["hard"]
		self.buttons = {pos: util.cast(QPushButton()) for pos in product(range(r), range(c))}
		for pos, button in self.buttons.items():
			button.pos, button.pressed, button.flagged, button.hint = pos, False, False, tuple()
			button.mousePressEvent = lambda event, b=button: self.press_mouse(event, b)
			button.mouseReleaseEvent = lambda event, b=button: self.release_mouse(event, b)
			button.setFixedSize(self.SIZE["block"], self.SIZE["block"])
			button.setFont(QFont("Rockwell Extra Bold", 15, QFont.Weight.Bold))
			self.gridLayout.addWidget(button, *pos)
			if pos[0] >= self.DIFFICULTY["easy"][0] or pos[1] >= self.DIFFICULTY["easy"][1]:
				button.hide()

		self.MINEFIELD = {d: np.zeros((r, c), dtype=np.uint8) for d, (r, c, _) in self.DIFFICULTY.items()}
		self.WINDOW_SIZE = {d: (
			self.SIZE["block"] * c + self.SIZE["gap"] * (c - 1) + 18,
			self.SIZE["block"] * r + self.SIZE["gap"] * (r - 1) + 55
		) for d, (r, c, _) in self.DIFFICULTY.items()}
		self.WINDOW_POS = {d: (
			(app.primaryScreen().size().width() - self.WINDOW_SIZE[d][0]) // 2,
			(app.primaryScreen().size().height() - self.WINDOW_SIZE[d][1]) // 2
		) for d in self.DIFFICULTY}

		self.difficulty = "easy"
		self.r = self.c = self.m = self.minefield = self.surrounding = self.platform = None
		self.pressed = self.flagged = 0
		self.timer = util.timer(10, self.timeout)
		self.radioButton_easy.click()

	def switch(self, difficulty):
		r_pre, c_pre, _ = self.DIFFICULTY[self.difficulty]
		r_sub, c_sub, _ = self.DIFFICULTY[difficulty]
		if c_pre != c_sub:
			r_max, c_max = max(r_pre, r_sub), max(c_pre, c_sub)
			r_min, c_min = min(r_pre, r_sub), min(c_pre, c_sub)
			hidden = c_pre > c_sub
			for pos in product(range(r_max), range(c_max)):
				if pos[0] >= r_min or pos[1] >= c_min:
					self.buttons[pos].setHidden(hidden)

		self.difficulty = difficulty
		self.r, self.c, self.m = self.DIFFICULTY[self.difficulty]
		self.minefield = self.MINEFIELD[self.difficulty]
		self.surrounding = CACHE["surrounding"][self.difficulty]
		self.platform = CACHE["platform"][self.difficulty]

		self.window().setFixedSize(*self.WINDOW_SIZE[self.difficulty])
		self.window().move(*self.WINDOW_POS[self.difficulty])
		self.restart()

	def restart(self):
		self.minefield.fill(0)
		self.pressed = self.flagged = 0

		self.timer.stop()
		self.timer.time = 0

		for pos, button in self.buttons.items():
			button.setText("")
			button.pressed = button.flagged = False
			button.setIcon(util.icon(None))
			button.setStyleSheet(self.QSS["unexplored"])
		self.statusbar.showMessage(self.MESSAGE % (self.m, 0))

	def press_mouse(self, event, button):
		if event.buttons() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
			return
		if event.buttons() == Qt.MouseButton.LeftButton and button.flagged:
			return

		if event.buttons() == Qt.MouseButton.LeftButton and not self.pressed:
			mines = random.sample(self.platform[button.pos], self.m)
			self.minefield[*zip(*mines)] = 9
			for pos in mines:
				for s in self.surrounding[pos]:
					self.minefield[s] += self.minefield[s] != 9
			self.timer.start()

		if not button.pressed:
			if event.buttons() == Qt.MouseButton.LeftButton:
				self.sweep(button.pos)
			else:
				button.flagged = not button.flagged
				button.setIcon(util.icon("../minesweeper/flag" if button.flagged else None))
				self.flagged += 1 if button.flagged else -1
				self.statusbar.showMessage(self.MESSAGE % (self.m - self.flagged, round(self.timer.time)))
		elif self.minefield[button.pos] != 0:
			surrounding = self.surrounding[button.pos]
			unflagged = tuple(s for s in surrounding if not self.buttons[s].pressed and not self.buttons[s].flagged)
			if self.minefield[button.pos] == sum(self.buttons[s].flagged for s in surrounding):
				for u in unflagged:
					self.sweep(u)
			else:
				for u in unflagged:
					self.buttons[u].setStyleSheet(self.QSS["hint"])
				self.buttons[button.pos].hint = unflagged

	def release_mouse(self, _, button):
		for pos in button.hint:
			self.buttons[pos].setStyleSheet(self.QSS["unexplored"])

	def sweep(self, pos):
		if self.minefield[pos] == 9:
			return self.judge("You lose", "error")

		self.expand(pos)
		self.statusbar.showMessage(self.MESSAGE % (self.m - self.flagged, round(self.timer.time)))

		if self.pressed == self.r * self.c - self.m:
			return self.judge("You win", "success")

	def judge(self, msg, msg_type):
		for pos in product(range(self.r), range(self.c)):
			if self.minefield[pos] == 9 and not self.buttons[pos].flagged:
				self.buttons[pos].setIcon(util.icon("../minesweeper/flag" if msg_type == "success" else "../minesweeper/mine"))
			elif self.minefield[pos] != 9 and self.buttons[pos].flagged:
				self.buttons[pos].setIcon(util.icon("../minesweeper/misjudged"))
		self.timer.stop()
		self.statusbar.showMessage(self.MESSAGE % (0, round(self.timer.time)))
		util.dialog(msg, msg_type)
		self.restart()

	def expand(self, pos):
		button = self.buttons[pos]
		if button.pressed or button.flagged:
			return

		button.pressed = True
		button.setText(str(self.minefield[pos]).strip("0"))
		button.setStyleSheet(self.QSS["explored"] % self.COLOR[self.minefield[pos]])
		self.pressed += 1

		if self.minefield[pos] == 0:
			for s in self.surrounding[pos]:
				self.expand(s)

	def timeout(self):
		self.timer.time += 0.01
		if self.timer.time >= 999:
			self.timer.stop()
		self.statusbar.showMessage(self.MESSAGE % (self.m - self.flagged, round(self.timer.time)))

	def leaveEvent(self, event):
		if self.pressed and self.timer.isActive():
			self.timer.stop()

	def enterEvent(self, event):
		if self.pressed and not self.timer.isActive():
			self.timer.start()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
