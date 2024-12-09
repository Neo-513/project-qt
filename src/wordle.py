from wordle_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow
from collections import defaultdict
from functools import partial
from itertools import chain
import os
import random
import sys
import util

_QSS_BASIC = "font-family: 'nyt-franklin'; color: %s; background-color: %s;"
_QSS_BUTTON = (
	"QPushButton {" + _QSS_BASIC + " border-radius: 5px}"
	"QPushButton:hover {background-color: %s}"
	"QPushButton:pressed {background-color: %s}"
)
QSS_LABEL = {
	"without_text": _QSS_BASIC % ("black", "white") + "border: 2px solid rgb(211,214,218);",
	"with_text": _QSS_BASIC % ("black", "white") + "border: 2px solid rgb(135,138,140);",
	"0": _QSS_BASIC % ("white", "rgb(120,124,126)"),
	"1": _QSS_BASIC % ("white", "rgb(198,180,86)"),
	"2": _QSS_BASIC % ("white", "rgb(112,169,97)")
}
QSS_BUTTON = {
	None: _QSS_BUTTON % ("black", "rgb(211,214,218)", "rgb(181,184,188)", "rgb(151,154,158)"),
	"0": _QSS_BUTTON % ("white", "rgb(120,124,126)", "rgb(90,94,96)", "rgb(60,64,66)"),
	"1": _QSS_BUTTON % ("white", "rgb(198,180,86)", "rgb(168,150,56)", "rgb(138,120,26)"),
	"2": _QSS_BUTTON % ("white", "rgb(112,169,97)", "rgb(82,139,67)", "rgb(52,109,37)")
}

KEY = {getattr(Qt.Key, f"Key_{chr(i)}"): chr(i) for i in range(65, 91)}
KEY.update({Qt.Key.Key_Return: "ENTER", Qt.Key.Key_Backspace: "DELETE"})

ALLOWED_WORDS = util.FileIO.read(os.path.join(util.RESOURCE, "wordle/allowed_words.txt")).splitlines()
POSSIBLE_WORDS = util.FileIO.read(os.path.join(util.RESOURCE, "wordle/possible_words.txt")).splitlines()
ROW_COUNT, COL_COUNT = 6, 5


class QtCore(QMainWindow, Ui_MainWindow):
	guesses, answer, round = None, None, None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../wordle/mosaic"))

		self.LABEL = [[getattr(self, f"label_{i}{j}") for j in range(COL_COUNT)] for i in range(ROW_COUNT)]
		self.BUTTON = {chr(i): getattr(self, f"pushButton_{chr(i + 32)}") for i in range(65, 91)}
		self.BUTTON.update({"ENTER": self.pushButton_enter, "DELETE": self.pushButton_delete})
		for name, button in self.BUTTON.items():
			util.button(button, partial(self.compute, key=name))

		util.button(self.toolButton, self.restart, "../wordle/restart")
		self.restart()

	def restart(self):
		self.guesses, self.answer, self.round = [""] * ROW_COUNT, random.choice(POSSIBLE_WORDS).lower(), 0
		self.label_message.clear()
		for label in chain.from_iterable(self.LABEL):
			label.clear()
			label.setStyleSheet(QSS_LABEL["without_text"])
		for button in self.BUTTON.values():
			button.setStyleSheet(QSS_BUTTON[None])

	def compute(self, key):
		if self.label_message.text().startswith("You"):
			return
		self.label_message.clear()

		guess = self.guesses[self.round]
		if key == "ENTER":
			if len(guess) < COL_COUNT:
				return self.label_message.setText("Not enough letters")
			if guess not in ALLOWED_WORDS:
				return self.label_message.setText("Word not found")

			state = ["2" if g == self.answer[i] else str(int(g in self.answer)) for i, g in enumerate(guess)]
			stas = defaultdict(set)

			for i, label in enumerate(self.LABEL[self.round]):
				label.setStyleSheet(QSS_LABEL[state[i]])
				stas[label.text()].add(state[i])
			for letter, sta in stas.items():
				sta = list(sta)[0] if len(sta) == 1 else "1"
				self.BUTTON[letter].setStyleSheet(QSS_BUTTON[sta])
			self.round += 1

			if state == ["2"] * COL_COUNT:
				return self.label_message.setText("You won")
			if self.round >= ROW_COUNT:
				return self.label_message.setText("You lose! The answer is " + self.answer.upper())
		elif key == "DELETE":
			if len(guess):
				self.guesses[self.round] = guess[:-1]
				self.LABEL[self.round][len(guess) - 1].clear()
				self.LABEL[self.round][len(guess) - 1].setStyleSheet(QSS_LABEL["without_text"])
		elif len(guess) < COL_COUNT:
			self.guesses[self.round] = guess + key.lower()
			self.LABEL[self.round][len(guess)].setText(key)
			self.LABEL[self.round][len(guess)].setStyleSheet(QSS_LABEL["with_text"])

	def keyPressEvent(self, event):
		if event.key() in KEY:
			self.compute(KEY[event.key()])


if __name__ == "__main__":
	app = QApplication(sys.argv)
	qt_core = QtCore()
	qt_core.setFixedSize(qt_core.width(), qt_core.height())
	qt_core.show()
	sys.exit(app.exec())
