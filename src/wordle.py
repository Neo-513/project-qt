from src.wordle_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QMainWindow
from functools import partial
from itertools import chain, product
import math
import numpy as np
import os
import random
import string
import sys
import src.util as util

QSS = {
	"label": "color: %s; background-color: %s; border: %spx solid %s",
	"button": (
		"QPushButton {color: %s; background-color: %s; border-radius: 5px}"
		"QPushButton:hover {background-color: %s}"
		"QPushButton:pressed {background-color: %s}"
	)
}
QSS_LABEL = {
	"nontext": QSS["label"] % ("black", "white", 2, "rgb(211,214,218)"),
	"text": QSS["label"] % ("black", "white", 2, "rgb(135,138,140)"),
	"hint": QSS["label"] % ("rgb(181,184,188)", "white", 2, "rgb(211,214,218)"),
	"hit": QSS["label"] % ("rgb(200,0,0)", "white", 2, "rgb(200,0,0)"),
	0: QSS["label"] % ("white", "rgb(120,124,126)", 0, "white"),
	1: QSS["label"] % ("white", "rgb(198,180,86)", 0, "white"),
	2: QSS["label"] % ("white", "rgb(112,169,97)", 0, "white")
}
QSS_BUTTON = {
	None: QSS["button"] % ("black", "rgb(211,214,218)", "rgb(181,184,188)", "rgb(151,154,158)"),
	0: QSS["button"] % ("white", "rgb(120,124,126)", "rgb(90,94,96)", "rgb(60,64,66)"),
	1: QSS["button"] % ("white", "rgb(198,180,86)", "rgb(168,150,56)", "rgb(138,120,26)"),
	2: QSS["button"] % ("white", "rgb(112,169,97)", "rgb(82,139,67)", "rgb(52,109,37)")
}

PATH = {
	"index": util.join_path(util.RESOURCE, "wordle", "cache_index.pkl"),
	"state": util.join_path(util.RESOURCE, "wordle", "cache_state.bin"),
	"worst": util.join_path(util.RESOURCE, "wordle", "cache_worst.pkl")
}
CACHE = {
	"index": util.FileIO.read(PATH["index"]) if os.path.exists(PATH["index"]) else None,
	"state": np.fromfile(PATH["state"], dtype=np.uint8) if os.path.exists(PATH["state"]) else None,
	"worst": util.FileIO.read(PATH["worst"]) if os.path.exists(PATH["worst"]) else None
}

ALLOWED_WORDS = tuple(util.FileIO.read(util.join_path(util.RESOURCE, "wordle", "allowed_words.txt")).splitlines())
POSSIBLE_WORDS = tuple(util.FileIO.read(util.join_path(util.RESOURCE, "wordle", "possible_words.txt")).splitlines())

TOTALITY = len(ALLOWED_WORDS)
TERNARY = tuple(product(range(3), repeat=5))
KEY = {getattr(Qt.Key, f"Key_{key.upper()}"): key for key in string.ascii_lowercase}


class MyCore(QMainWindow, Ui_MainWindow):
	guesses, states, alphabet = None, None, None
	answer, inning = None, None
	hints, candidate = None, None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../wordle/mosaic"))

		self.LABEL = [[getattr(self, f"label_{i}{j}") for j in range(5)] for i in range(6)]
		for label in chain.from_iterable(self.LABEL):
			label.setFont(QFont("nyt-franklin", 21, QFont.Weight.Bold))
			label.setAlignment(Qt.AlignmentFlag.AlignCenter)

		self.BUTTON = {key: getattr(self, f"pushButton_{key}") for key in str(string.ascii_lowercase)}
		for key, button in self.BUTTON.items():
			button.setFont(QFont("nyt-franklin", 16, QFont.Weight.Bold))
			button.setText(key.upper())
			util.button(button, partial(self.send_letter, key=key))

		self.pushButton_enter.setText("ENTER")
		self.pushButton_enter.setFont(QFont("nyt-franklin", 12, QFont.Weight.Bold))
		self.pushButton_enter.setStyleSheet(QSS_BUTTON[None])

		self.pushButton_delete.setText("⌫")
		self.pushButton_delete.setFont(QFont("nyt-franklin", 16, QFont.Weight.Bold))
		self.pushButton_delete.setStyleSheet(QSS_BUTTON[None])

		util.button(self.pushButton_enter, self.send_enter)
		util.button(self.pushButton_delete, self.send_delete)
		util.button(self.toolButton_restart, self.restart, "../wordle/restart", tip="新游戏")
		util.button(self.toolButton_hinting, self.hinting, "../wordle/hint", tip="提示", ico_size=32)
		self.restart()

	def restart(self):
		self.guesses, self.states, self.alphabet = [""] * 6, [-1] * 6, set()
		self.answer, self.inning = random.choice(POSSIBLE_WORDS), 0
		self.hints, self.candidate = [""] * 6, ALLOWED_WORDS

		for label in chain.from_iterable(self.LABEL):
			label.clear()
			label.setStyleSheet(QSS_LABEL["nontext"])
		for button in self.BUTTON.values():
			button.setStyleSheet(QSS_BUTTON[None])
		self.label_message.clear()

	def hinting(self):
		if self.label_message.text().startswith("You"):
			return
		if not self.inning:
			return
		if self.hints[self.inning]:
			return

		guess, state = self.guesses[self.inning - 1], self.states[self.inning - 1]
		if self.inning == 1 and state == 0:
			self.hints[self.inning] = CACHE["worst"][guess]
		else:
			self.hints[self.inning] = EntropyAlgorithm.infer(self.candidate)
		MyDisplayer.label()

	def keyPressEvent(self, a0):
		if a0.key() == Qt.Key.Key_Return:
			return self.send_enter()
		if a0.key() == Qt.Key.Key_Backspace:
			return self.send_delete()
		if a0.key() in KEY:
			return self.send_letter(KEY[a0.key()])

	def send_enter(self):
		if self.label_message.text().startswith("You"):
			return
		self.label_message.clear()

		guess = self.guesses[self.inning]
		if len(guess) < 5:
			return self.label_message.setText("Not enough letters")
		if guess not in ALLOWED_WORDS:
			return self.label_message.setText("Word not found")

		state = int(MyComputation.to_state(guess, self.answer))
		self.states[self.inning] = state
		self.candidate = MyComputation.to_candidate(guess, state, self.candidate)

		MyDisplayer.label()
		MyDisplayer.button()
		self.inning += 1

		if state == 242:
			return self.label_message.setText("You win")
		if self.inning >= 6:
			return self.label_message.setText("You lose! The answer is " + self.answer.upper())

	def send_delete(self):
		if self.label_message.text().startswith("You"):
			return
		self.label_message.clear()

		self.guesses[self.inning] = self.guesses[self.inning][:-1]
		MyDisplayer.label()

	def send_letter(self, key):
		if self.label_message.text().startswith("You"):
			return
		self.label_message.clear()

		if len(self.guesses[self.inning]) < 5:
			self.guesses[self.inning] += key
			MyDisplayer.label()


class MyDisplayer:
	@staticmethod
	def label():
		guess = my_core.guesses[my_core.inning]
		state = my_core.states[my_core.inning]
		hint = my_core.hints[my_core.inning]

		if state != -1:
			for i, label in enumerate(my_core.LABEL[my_core.inning]):
				label.setText(guess[i].upper())
				label.setStyleSheet(QSS_LABEL[TERNARY[state][i]])
			return

		for i, label in enumerate(my_core.LABEL[my_core.inning]):
			if i < len(guess):
				my_core.LABEL[my_core.inning][i].setText(guess[i].upper())
				my_core.LABEL[my_core.inning][i].setStyleSheet(QSS_LABEL["text"])
			elif hint:
				label.setText(hint[i].upper())
				label.setStyleSheet(QSS_LABEL["hit" if len(my_core.candidate) == 1 else "hint"])
			else:
				label.clear()
				label.setStyleSheet(QSS_LABEL["nontext"])

	@staticmethod
	def button():
		guess = my_core.guesses[my_core.inning]
		state = TERNARY[my_core.states[my_core.inning]]

		for s, (i, g) in product((0, 2), enumerate(guess)):
			if state[i] == s:
				my_core.BUTTON[g].setStyleSheet(QSS_BUTTON[s])
				my_core.alphabet.add(g)

		for i, g in enumerate(guess):
			if state[i] == 1 and g not in my_core.alphabet:
				my_core.BUTTON[g].setStyleSheet(QSS_BUTTON[state[i]])


class MyComputation:
	@staticmethod
	def to_state(guess, answer):
		index_guess, index_answer = CACHE["index"][guess], CACHE["index"][answer]
		return CACHE["state"][index_guess * TOTALITY + index_answer]

	@staticmethod
	def to_candidate(guess, state, candidate):
		return tuple(answer for answer in candidate if MyComputation.to_state(guess, answer) == state)


class EntropyAlgorithm:
	@staticmethod
	def infer(candidate):
		n, nlog = len(candidate), math.log2(len(candidate))
		return max(candidate, key=lambda guess: EntropyAlgorithm.to_entropy(guess, candidate, n, nlog))

	@staticmethod
	def to_entropy(guess, candidate, n, nlog):
		states = [MyComputation.to_state(guess, answer) for answer in candidate]
		counts = np.bincount(np.array(states))
		counts = counts[counts != 0]
		return nlog - np.sum(counts * np.log2(counts)) / n


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
