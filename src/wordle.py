from wordle_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QSizePolicy
from functools import partial
from itertools import product
from string import ascii_lowercase
import math
import numpy as np
import os
import random
import sys
import util

ALLOWED_WORDS = tuple(util.read(util.join_path(util.RESOURCE, "wordle", "allowed_words.txt")).splitlines())
POSSIBLE_WORDS = tuple(util.read(util.join_path(util.RESOURCE, "wordle", "possible_words.txt")).splitlines())

PATH = {
	"index": util.join_path(util.RESOURCE, "wordle", "cache_index.pkl"),
	"compose": util.join_path(util.RESOURCE, "wordle", "cache_compose.pkl"),
	"state": util.join_path(util.RESOURCE, "wordle", "cache_state.bin"),
	"worst_00000": util.join_path(util.RESOURCE, "wordle", "cache_worst_00000.pkl"),
	"worst_00001": util.join_path(util.RESOURCE, "wordle", "cache_worst_00001.pkl"),
	"worst_00010": util.join_path(util.RESOURCE, "wordle", "cache_worst_00010.pkl"),
	"worst_00100": util.join_path(util.RESOURCE, "wordle", "cache_worst_00100.pkl"),
	"worst_01000": util.join_path(util.RESOURCE, "wordle", "cache_worst_01000.pkl"),
	"worst_10000": util.join_path(util.RESOURCE, "wordle", "cache_worst_10000.pkl")
}
CACHE = {
	"index": util.read(PATH["index"]) if os.path.exists(PATH["index"]) else None,
	"compose": util.read(PATH["compose"]) if os.path.exists(PATH["compose"]) else None,
	"state": np.fromfile(PATH["state"], dtype=np.uint8) if os.path.exists(PATH["state"]) else None,
	"worst_00000": util.read(PATH["worst_00000"]) if os.path.exists(PATH["worst_00000"]) else None,
	"worst_00001": util.read(PATH["worst_00001"]) if os.path.exists(PATH["worst_00001"]) else None,
	"worst_00010": util.read(PATH["worst_00010"]) if os.path.exists(PATH["worst_00010"]) else None,
	"worst_00100": util.read(PATH["worst_00100"]) if os.path.exists(PATH["worst_00100"]) else None,
	"worst_01000": util.read(PATH["worst_01000"]) if os.path.exists(PATH["worst_01000"]) else None,
	"worst_10000": util.read(PATH["worst_10000"]) if os.path.exists(PATH["worst_10000"]) else None
}


class MyCore(QMainWindow, Ui_MainWindow):
	KEY = {getattr(Qt.Key, f"Key_{key.upper()}"): key for key in ascii_lowercase}
	TERNARY = tuple("".join(map(str, t)) for t in product(range(3), repeat=5))
	DPR = util.screen()["dpr"]
	FONT = {
		12: QFont("nyt-franklin", 12, QFont.Weight.Bold),
		16: QFont("nyt-franklin", 16, QFont.Weight.Bold),
		21: QFont("nyt-franklin", 16, QFont.Weight.Bold)
	}
	IMG = {
		"state": {s: {c: util.image(f"../wordle/{s}_{c}") for c in ascii_lowercase} for s in "012"},
		"hint": {c: util.image(f"../wordle/hint_{c}") for c in ascii_lowercase},
		"hit": {c: util.image(f"../wordle/hit_{c}") for c in ascii_lowercase},
		"text": {c: util.image(f"../wordle/text_{c}") for c in ascii_lowercase},
		"nontext": util.image(f"../wordle/nontext")
	}

	QSS = (
		"QPushButton {color: %s; background-color: %s; border-radius: 5px}"
		"QPushButton:hover {background-color: %s}"
		"QPushButton:pressed {background-color: %s}"
	)
	BUTTON = {
		None: QSS % ("black", "rgb(211,214,218)", "rgb(181,184,188)", "rgb(151,154,158)"),
		"0": QSS % ("white", "rgb(120,124,126)", "rgb(90,94,96)", "rgb(60,64,66)"),
		"1": QSS % ("white", "rgb(198,180,86)", "rgb(168,150,56)", "rgb(138,120,26)"),
		"2": QSS % ("white", "rgb(112,169,97)", "rgb(82,139,67)", "rgb(52,109,37)")
	}
	
	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../wordle/logo"))

		self.labels = {(i, j): getattr(self, f"label_{i}{j}") for i, j in product(range(6), range(5))}
		for label in self.labels.values():
			label.setFont(self.FONT[12])
			label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

		self.buttons = {key: getattr(self, f"pushButton_{key}") for key in ascii_lowercase}
		for key, button in self.buttons.items():
			button.setText(key.upper())
			button.setFont(self.FONT[16])
			util.button(button, partial(self.act, key=key))

		self.pushButton_enter.setText("ENTER")
		self.pushButton_enter.setFont(self.FONT[12])
		self.pushButton_enter.setStyleSheet(self.BUTTON[None])

		self.pushButton_delete.setText("⌫")
		self.pushButton_delete.setFont(self.FONT[16])
		self.pushButton_delete.setStyleSheet(self.BUTTON[None])

		util.button(self.pushButton_enter, lambda: self.act("enter"))
		util.button(self.pushButton_delete, lambda: self.act("delete"))
		util.button(self.toolButton_restart, self.restart, "../wordle/restart", tip="新游戏", ico_size=40)
		util.button(self.toolButton_hinting, self.hinting, "../wordle/nonhint", tip="提示", ico_size=32)
		
		self.guess = self.answer = self.inning = self.hint = self.candidate = None
		self.alphabet, self.show_hint = set(), False
		self.timer = util.timer(30, self.timeout)
		self.restart()

	def restart(self):
		if self.timer.isActive():
			self.timer.stop()

		self.guess, self.answer, self.inning = "", random.choice(POSSIBLE_WORDS), 0
		self.hint, self.candidate = None, ALLOWED_WORDS
		self.alphabet.clear()

		for i, j in product(range(6), range(5)):
			self.display(i, j, self.IMG["nontext"])
		for button in self.buttons.values():
			button.setStyleSheet(self.BUTTON[None])
		self.label_message.clear()

	def hinting(self):
		if self.timer.isActive():
			return

		self.show_hint = not self.show_hint
		self.toolButton_hinting.setIcon(util.icon("../wordle/hint" if self.show_hint else "../wordle/nonhint"))

		if self.label_message.text().startswith("You"):
			return
		if not self.hint:
			return

		for i, h in enumerate(self.hint):
			if i >= len(self.guess):
				if self.show_hint:
					img = self.IMG["hit" if len(self.candidate) == 1 else "hint"][h]
				else:
					img = self.IMG["nontext"]
				self.display(self.inning, i, img)

	def keyPressEvent(self, event):
		if event.key() == Qt.Key.Key_Return:
			return self.act("enter")
		if event.key() == Qt.Key.Key_Backspace:
			return self.act("delete")
		if event.key() in MyCore.KEY:
			return self.act(MyCore.KEY[event.key()])

	def act(self, key):
		if self.timer.isActive():
			return
		if self.label_message.text().startswith("You"):
			return
		self.label_message.clear()

		if key == "enter":
			if len(self.guess) < 5:
				return self.label_message.setText("Not enough letters")
			if self.guess not in ALLOWED_WORDS:
				return self.label_message.setText("Word not found")

			state = MyComputation.to_state(self.guess, self.answer)
			state_ternary = self.TERNARY[state]
			self.candidate = MyComputation.to_candidate(self.guess, state, self.candidate)
			if self.inning > 0 and f"worst_{state_ternary}" in CACHE:
				self.hint = CACHE[f"worst_{state_ternary}"][self.guess]
			else:
				self.hint = EntropyAlgorithm.solve(self.candidate)

			self.timer.frame = 0
			self.timer.state = state_ternary
			self.timer.previous = tuple(QPixmap(self.IMG["text"][g]) for i, g in enumerate(self.guess))
			self.timer.subsequent = tuple(QPixmap(self.IMG["state"][state_ternary[i]][g]) for i, g in enumerate(self.guess))
			self.timer.start()
		elif key == "delete":
			if len(self.guess) > 0:
				self.guess = self.guess[:-1]
				if self.show_hint and self.hint:
					img = self.IMG["hit" if len(self.candidate) == 1 else "hint"][tuple(self.hint)[len(self.guess)]]
				else:
					img = self.IMG["nontext"]
				self.display(self.inning, len(self.guess), img)
		else:
			if len(self.guess) < 5:
				self.guess += key
				self.display(self.inning, len(self.guess) - 1, self.IMG["text"][key])

	def display(self, x, y, img):
		pixmap = QPixmap(img)
		pixmap.setDevicePixelRatio(self.DPR)
		self.labels[x, y].setPixmap(pixmap)

	def timeout(self):
		if self.timer.frame >= 50:
			self.timer.stop()
			for i, g in enumerate(self.guess):
				self.display(self.inning, i, self.IMG["state"][self.timer.state[i]][g])
			if self.show_hint and self.hint and self.guess != self.answer:
				for i, h in enumerate(self.hint):
					self.display(self.inning + 1, i, self.IMG["hit" if len(self.candidate) == 1 else "hint"][h])

			for s, (i, g) in product("02", enumerate(self.guess)):
				if self.timer.state[i] == s:
					self.buttons[g].setStyleSheet(self.BUTTON[s])
					self.alphabet.add(g)
			for i, g in enumerate(self.guess):
				if self.timer.state[i] == "1" and g not in self.alphabet:
					self.buttons[g].setStyleSheet(self.BUTTON[self.timer.state[i]])

			if self.guess == self.answer:
				self.label_message.setText("You win")
			elif self.inning >= 5:
				self.label_message.setText("You lose! The answer is " + self.answer.upper())
			else:
				self.guess = ""
				self.inning += 1
			return

		pixmap = (self.timer.previous if self.timer.frame % 10 < 5 else self.timer.subsequent)[self.timer.frame // 10]
		ratio = abs(1 - (self.timer.frame + 1) % 10 / 5)
		img = pixmap.scaled(pixmap.width(), round(pixmap.height() * ratio)).toImage()
		self.display(self.inning, self.timer.frame // 10, img)
		self.timer.frame += 1


class MyComputation:
	TOTALITY = len(ALLOWED_WORDS)

	@staticmethod
	def to_state(guess, answer):
		index_guess, index_answer = CACHE["index"][guess], CACHE["index"][answer]
		return int(CACHE["state"][index_guess * MyComputation.TOTALITY + index_answer])

	@staticmethod
	def to_candidate(guess, state, candidate):
		return tuple(answer for answer in candidate if MyComputation.to_state(guess, answer) == state)


class EntropyAlgorithm:
	@staticmethod
	def solve(candidate):
		if candidate:
			n, nlog = len(candidate), math.log2(len(candidate))
			return max(candidate, key=lambda guess: EntropyAlgorithm.entropy(guess, candidate, n, nlog))

	@staticmethod
	def entropy(guess, candidate, n, nlog):
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
