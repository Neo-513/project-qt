from wordle_ui import Ui_MainWindow
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QSizePolicy
from functools import partial
from itertools import chain, product
from string import ascii_lowercase
import math
import numpy as np
import os
import random
import sys
import util

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
	"0": QSS["label"] % ("white", "rgb(120,124,126)", 0, "white"),
	"1": QSS["label"] % ("white", "rgb(198,180,86)", 0, "white"),
	"2": QSS["label"] % ("white", "rgb(112,169,97)", 0, "white")
}
QSS_BUTTON = {
	None: QSS["button"] % ("black", "rgb(211,214,218)", "rgb(181,184,188)", "rgb(151,154,158)"),
	"0": QSS["button"] % ("white", "rgb(120,124,126)", "rgb(90,94,96)", "rgb(60,64,66)"),
	"1": QSS["button"] % ("white", "rgb(198,180,86)", "rgb(168,150,56)", "rgb(138,120,26)"),
	"2": QSS["button"] % ("white", "rgb(112,169,97)", "rgb(82,139,67)", "rgb(52,109,37)")
}

PATH = {
	"index": util.join_path(util.RESOURCE, "wordle", "cache_index.pkl"),
	"state": util.join_path(util.RESOURCE, "wordle", "cache_state.bin"),
	"worst_00000": util.join_path(util.RESOURCE, "wordle", "cache_worst_00000.pkl"),
	"worst_00001": util.join_path(util.RESOURCE, "wordle", "cache_worst_00001.pkl"),
	"worst_00010": util.join_path(util.RESOURCE, "wordle", "cache_worst_00010.pkl"),
	"worst_00100": util.join_path(util.RESOURCE, "wordle", "cache_worst_00100.pkl"),
	"worst_01000": util.join_path(util.RESOURCE, "wordle", "cache_worst_01000.pkl"),
	"worst_10000": util.join_path(util.RESOURCE, "wordle", "cache_worst_10000.pkl")
}
CACHE = {
	"index": util.FileIO.read(PATH["index"]) if os.path.exists(PATH["index"]) else None,
	"state": np.fromfile(PATH["state"], dtype=np.uint8) if os.path.exists(PATH["state"]) else None,
	"worst_00000": util.FileIO.read(PATH["worst_00000"]) if os.path.exists(PATH["worst_00000"]) else None,
	"worst_00001": util.FileIO.read(PATH["worst_00001"]) if os.path.exists(PATH["worst_00001"]) else None,
	"worst_00010": util.FileIO.read(PATH["worst_00010"]) if os.path.exists(PATH["worst_00010"]) else None,
	"worst_00100": util.FileIO.read(PATH["worst_00100"]) if os.path.exists(PATH["worst_00100"]) else None,
	"worst_01000": util.FileIO.read(PATH["worst_01000"]) if os.path.exists(PATH["worst_01000"]) else None,
	"worst_10000": util.FileIO.read(PATH["worst_10000"]) if os.path.exists(PATH["worst_10000"]) else None
}

ALLOWED_WORDS = tuple(util.FileIO.read(util.join_path(util.RESOURCE, "wordle", "allowed_words.txt")).splitlines())
POSSIBLE_WORDS = tuple(util.FileIO.read(util.join_path(util.RESOURCE, "wordle", "possible_words.txt")).splitlines())

TOTALITY = len(ALLOWED_WORDS)
TERNARY = tuple("".join(map(str, t)) for t in product(range(3), repeat=5))
KEY = {getattr(Qt.Key, f"Key_{key.upper()}"): key for key in ascii_lowercase}

DPR = util.screen_info()["dpr"]
PIXMAP_SIZE = 52


class MyCore(QMainWindow, Ui_MainWindow):
	guess = state = answer = inning = hint = candidate = None
	alphabet, show_hint = set(), False

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../wordle/logo"))

		self.timer = QTimer()
		self.timer.setInterval(30)
		util.cast(self.timer).timeout.connect(lambda: MyDisplayer.display_animate(self))

		self.LABEL = [[getattr(self, f"label_{i}{j}") for j in range(5)] for i in range(6)]
		for label in chain.from_iterable(self.LABEL):
			label.setFont(QFont("nyt-franklin", 21, QFont.Weight.Bold))
			label.setAlignment(Qt.AlignmentFlag.AlignCenter)
			label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

		self.BUTTON = {key: getattr(self, f"pushButton_{key}") for key in ascii_lowercase}
		for key, button in self.BUTTON.items():
			button.setFont(QFont("nyt-franklin", 16, QFont.Weight.Bold))
			button.setText(key.upper())
			util.button(button, partial(self.send_key, key=key))

		self.pushButton_enter.setText("ENTER")
		self.pushButton_enter.setFont(QFont("nyt-franklin", 12, QFont.Weight.Bold))
		self.pushButton_enter.setStyleSheet(QSS_BUTTON[None])

		self.pushButton_delete.setText("⌫")
		self.pushButton_delete.setFont(QFont("nyt-franklin", 16, QFont.Weight.Bold))
		self.pushButton_delete.setStyleSheet(QSS_BUTTON[None])

		util.button(self.pushButton_enter, lambda: self.send_key("enter"))
		util.button(self.pushButton_delete, lambda: self.send_key("delete"))
		util.button(self.toolButton_restart, self.restart, "../wordle/restart", tip="新游戏")
		util.button(self.toolButton_hinting, self.hinting, "../wordle/nonhint", tip="提示", ico_size=32)
		self.restart()

	def restart(self):
		if self.timer.isActive():
			self.timer.stop()

		self.guess, self.state = "", None
		self.answer, self.inning = random.choice(POSSIBLE_WORDS), 0
		self.alphabet.clear()
		self.hint, self.candidate = None, ALLOWED_WORDS

		for labels in self.LABEL:
			MyDisplayer.display_clear(labels)
		for button in self.BUTTON.values():
			button.setStyleSheet(QSS_BUTTON[None])
		self.label_message.clear()

	def hinting(self):
		if self.timer.isActive():
			return

		self.show_hint = not self.show_hint
		self.toolButton_hinting.setIcon(util.icon("../wordle/hint" if self.show_hint else "../wordle/nonhint"))

		if not self.label_message.text().startswith("You"):
			MyDisplayer.display_clear(self.LABEL[self.inning])
			MyDisplayer.display_label(self.guess, self.state, self.LABEL[self.inning], self.state is not None)
			MyDisplayer.display_hint(self, self.LABEL[self.inning])

	def keyPressEvent(self, a0):
		if a0.key() == Qt.Key.Key_Return:
			self.send_key("enter")
		elif a0.key() == Qt.Key.Key_Backspace:
			self.send_key("delete")
		elif a0.key() in KEY:
			self.send_key(KEY[a0.key()])

	def send_key(self, key):
		if self.timer.isActive():
			return
		if self.label_message.text().startswith("You"):
			return
		self.label_message.clear()

		if key == "enter":
			self.__enter()
		elif key == "delete":
			self.__delete()
		else:
			self.__letter(key)

	def __enter(self):
		if len(self.guess) < 5:
			return self.label_message.setText("Not enough letters")
		if self.guess not in ALLOWED_WORDS:
			return self.label_message.setText("Word not found")

		self.state = MyComputation.to_state(self.guess, self.answer)
		self.candidate = MyComputation.to_candidate(self.guess, self.state, self.candidate)
		if not self.inning and CACHE.get(f"worst_{TERNARY[self.state]}", None):
			self.hint = CACHE[f"worst_{TERNARY[self.state]}"][self.guess]
		else:
			self.hint = EntropyAlgorithm.infer(self.candidate)

		self.timer.frame = 0
		self.timer.inning = self.inning
		self.timer.previous = MyDisplayer.display_render(self.LABEL[self.inning])
		self.timer.subsequent = MyDisplayer.display_render(MyDisplayer.display_skeleton(self.guess, self.state))
		self.timer.start()

	def __delete(self):
		self.guess = self.guess[:-1]
		MyDisplayer.display_clear(self.LABEL[self.inning])
		MyDisplayer.display_label(self.guess, self.state, self.LABEL[self.inning], False)
		MyDisplayer.display_hint(self, self.LABEL[self.inning])

	def __letter(self, key):
		if len(self.guess) < 5:
			self.guess += key
			MyDisplayer.display_clear(self.LABEL[self.inning])
			MyDisplayer.display_label(self.guess, self.state, self.LABEL[self.inning], False)
			MyDisplayer.display_hint(self, self.LABEL[self.inning])


class MyDisplayer:
	@staticmethod
	def display_clear(labels):
		for i, label in enumerate(labels):
			label.clear()
			label.setStyleSheet(QSS_LABEL["nontext"])

	@staticmethod
	def display_label(guess, state, labels, stateful):
		for i in range(len(guess)):
			qss = QSS_LABEL[TERNARY[state][i]] if stateful else QSS_LABEL["text"]
			labels[i].setText(guess[i].upper())
			labels[i].setStyleSheet(qss)

	@staticmethod
	def display_hint(self, labels):
		if not self.show_hint:
			return
		if not self.hint:
			return
		if self.guess == self.answer:
			return

		qss = QSS_LABEL["hit" if len(self.candidate) == 1 else "hint"]
		for i, label in enumerate(labels):
			if self.state is not None or i >= len(self.guess):
				label.setText(self.hint[i].upper())
				label.setStyleSheet(qss)

	@staticmethod
	def display_button(self):
		state = TERNARY[self.state]
		for s, (i, g) in product("02", enumerate(self.guess)):
			if state[i] == s:
				self.BUTTON[g].setStyleSheet(QSS_BUTTON[s])
				self.alphabet.add(g)
		for i, g in enumerate(self.guess):
			if state[i] == "1" and g not in self.alphabet:
				self.BUTTON[g].setStyleSheet(QSS_BUTTON[state[i]])

	@staticmethod
	def display_skeleton(guess, state):
		labels = [QLabel() for _ in range(5)]
		for i, label in enumerate(labels):
			label.setFixedSize(PIXMAP_SIZE, PIXMAP_SIZE)
			label.setFont(QFont("nyt-franklin", 21, QFont.Weight.Bold))
			label.setAlignment(Qt.AlignmentFlag.AlignCenter)
			label.setText(guess[i].upper())
			label.setStyleSheet(QSS_LABEL[TERNARY[state][i]])
		return labels

	@staticmethod
	def display_render(labels):
		pixmaps = [QPixmap(int(DPR * PIXMAP_SIZE), int(DPR * PIXMAP_SIZE)) for _ in range(len(labels))]
		for i, label in enumerate(labels):
			pixmaps[i].setDevicePixelRatio(DPR)
			with QPainter(pixmaps[i]) as painter:
				label.render(painter)
		return pixmaps

	@staticmethod
	def display_animate(self):
		if self.timer.frame >= 50:
			self.timer.stop()
			MyDisplayer.display_label(self.guess, self.state, self.LABEL[self.timer.inning], True)
			MyDisplayer.display_hint(self, self.LABEL[self.timer.inning + 1]) if self.timer.inning <= 4 else None
			MyDisplayer.display_button(self)

			if self.guess == self.answer:
				self.label_message.setText("You win")
			elif self.inning >= 5:
				self.label_message.setText("You lose! The answer is " + self.answer.upper())
			else:
				self.guess, self.state, self.inning = "", None, self.inning + 1
			return

		label = self.LABEL[self.timer.inning][self.timer.frame // 10]
		pixmap = (self.timer.previous if self.timer.frame % 10 < 5 else self.timer.subsequent)[self.timer.frame // 10]
		ratio = abs(1 - (self.timer.frame + 1) % 10 / 5)

		label.setStyleSheet(None)
		label.setPixmap(pixmap.scaled(pixmap.width(), int(pixmap.height() * ratio)))
		self.timer.frame += 1


class MyComputation:
	@staticmethod
	def to_state(guess, answer):
		index_guess, index_answer = CACHE["index"][guess], CACHE["index"][answer]
		return int(CACHE["state"][index_guess * TOTALITY + index_answer])

	@staticmethod
	def to_candidate(guess, state, candidate):
		return tuple(answer for answer in candidate if MyComputation.to_state(guess, answer) == state)


class EntropyAlgorithm:
	@staticmethod
	def infer(candidate):
		if not candidate:
			return None
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
