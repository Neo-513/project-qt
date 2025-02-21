from wordle_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QMainWindow
from collections import Counter, defaultdict
from functools import partial
from itertools import chain, product
from multiprocessing import cpu_count, Pool
import math
import numpy as np
import os
import random
import string
import sys
import util



import time
import mylibrary.myutil as mu


class MyCore(QMainWindow, Ui_MainWindow):
	answer, inning = None, None
	guesses, states = None, None
	hints, candidate = None, None
	labels, buttons = [], []

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../wordle/mosaic"))

		self.labels = [[getattr(self, f"label_{i}{j}") for j in range(5)] for i in range(6)]
		for label in chain.from_iterable(self.labels):
			label.setFont(FONT_LABEL)
			label.setAlignment(Qt.AlignmentFlag.AlignCenter)

		self.buttons = {key: getattr(self, f"pushButton_{key}") for key in KEY.values()}
		for key, button in self.buttons.items():
			button.setFont(FONT_TEXT)
			button.setText(key.upper())
			util.button(button, partial(self.act, key=key))
		self.pushButton_delete.setText("⌫")
		self.pushButton_enter.setFont(FONT_ENTER)
		self.pushButton_delete.setFont(FONT_DELETE)

		util.button(self.toolButton_restart, self.restart, "../wordle/restart", tip="新游戏")
		util.button(self.toolButton_hinting, self.hinting, "../wordle/hint", tip="提示", ico_size=32)
		self.restart()

	def restart(self):
		self.answer, self.inning = random.choice(POSSIBLE_WORDS), 0
		self.guesses, self.states = [""] * 6, [-1] * 6
		self.hints, self.candidate = [""] * 6, ALLOWED_WORDS

		self.label_message.clear()
		for label in chain.from_iterable(self.labels):
			label.clear()
			label.setStyleSheet(QSS_LABEL["non_text"])
		for button in self.buttons.values():
			button.setStyleSheet(QSS_BUTTON[None])

	def hinting(self):
		if self.label_message.text().startswith("You"):
			return
		self.toolButton_hinting.clicked.disconnect(self.hinting)
		if self.inning and not self.hints[self.inning]:
			guess, state = self.guesses[self.inning - 1], self.states[self.inning - 1]
			self.candidate = MyComputation.to_candidate(guess, state, self.candidate, CACHE, TOTALITY)
			tictoc = time.time()
			if self.inning == 1 and state == 0:
				self.hints[self.inning] = CACHE["worst"][guess]
			else:
				self.hints[self.inning] = EntropyAlgorithm.infer(self.candidate, CACHE, TOTALITY, accelerate=len(self.candidate) >= 2000)
			print(f"{time.time() - tictoc} s {len(self.candidate)}")
			self.display_label()
		self.toolButton_hinting.clicked.connect(self.hinting)

	def keyPressEvent(self, a0):
		if a0.key() in KEY:
			self.act(KEY[a0.key()])

	def act(self, key):
		if self.label_message.text().startswith("You"):
			return
		self.label_message.clear()
		
		guess = self.guesses[self.inning]
		if key == "enter":
			if len(guess) < 5:
				return self.label_message.setText("Not enough letters")
			if guess not in ALLOWED_WORDS:
				return self.label_message.setText("Word not found")

			self.states[self.inning] = MyComputation.to_state(guess, self.answer, CACHE, TOTALITY)
			self.display_label()
			self.display_button()
			if self.states[self.inning] == 242:
				return self.label_message.setText("You win")

			self.inning += 1
			if self.inning >= 6:
				return self.label_message.setText("You lose! The answer is " + self.answer.upper())
		elif key == "delete":
			self.guesses[self.inning] = self.guesses[self.inning][:-1]
			self.display_label()
		elif len(self.guesses[self.inning]) < 5:
			self.guesses[self.inning] += key
			self.display_label()

	def display_label(self):
		guess, state = self.guesses[self.inning], self.states[self.inning]
		state = MyComputation.to_ternary(state)
		for j, label in enumerate(self.labels[self.inning]):
			if j < len(guess):
				label.setText(guess[j].upper())
				if state:
					label.setStyleSheet(QSS_LABEL[state[j]])
				else:
					label.setStyleSheet(QSS_LABEL["text"])
			else:
				if self.hints[self.inning]:
					label.setText(self.hints[self.inning][j].upper())
					if len(self.candidate) == 1:
						label.setStyleSheet(QSS_LABEL["hit"])
					else:
						label.setStyleSheet(QSS_LABEL["hint"])
				else:
					label.clear()
					label.setStyleSheet(QSS_LABEL["non_text"])

	def display_button(self):
		amounts = defaultdict(set)
		for j, g in enumerate(self.guesses[self.inning]):
			amounts[g].add(MyComputation.to_ternary(self.states[self.inning])[j])
		for letter, amount in amounts.items():
			state = amount.pop() if len(amount) == 1 else "1"
			self.buttons[letter].setStyleSheet(QSS_BUTTON[state])


class EntropyAlgorithm:
	@staticmethod
	def infer(candidate, cache, totality, accelerate=False):
		best_entropy, best_guess = 0, None
		if False:#accelerate:
			print("accelerate", len(candidate))
			tasks = ((guess, candidate, CACHE, TOTALITY) for guess in candidate)
			for guess, entropy in POOL.imap_unordered(EntropyAlgorithm.entropy, tasks):
				if entropy >= best_entropy:
					best_entropy, best_guess = entropy, guess
		else:
			print("candidate", len(candidate))
			for guess in candidate:
				_, entropy = EntropyAlgorithm.entropy((guess, candidate, cache, totality))
				if entropy >= best_entropy:
					best_entropy, best_guess = entropy, guess
		return best_guess

	@staticmethod
	def entropy(args):
		(guess, candidate, cache, totality), states = args, {}
		states.update((MyComputation.to_state(guess, answer, cache, totality), 1) for answer in candidate)
		entropy = math.log2(len(candidate)) - sum(s * math.log2(s) for s in states.values()) / len(candidate)
		return guess, entropy


class MyComputation:
	@staticmethod
	def to_mask(guess, answer):
		state, frequency = [""] * 5, CACHE["frequency"][answer].copy()
		for i, g in enumerate(guess):
			if g == answer[i]:
				state[i] = "2"
				frequency[g] -= 1
			elif g not in answer:
				state[i] = "0"
		for i, s in enumerate(state):
			if not s:
				if frequency[guess[i]]:
					state[i] = "1"
					frequency[guess[i]] -= 1
				else:
					state[i] = "0"
		return int("".join(state), 3)

	@staticmethod
	def to_state(guess, answer, cache, totality):
		index_guess = cache["index"][guess]
		index_answer = cache["index"][answer]
		return cache["state"][index_guess * totality + index_answer]

	@staticmethod
	def to_ternary(state):
		if state == -1:
			return ""
		ternary = ""
		while state > 0:
			ternary += str(state % 3)
			state //= 3
		return f"{ternary:05}"[::-1]

	@staticmethod
	def to_candidate(guess, state, candidate, cache, totality):
		return tuple(answer for answer in candidate if MyComputation.to_state(guess, answer, cache, totality) == state)


class MyPrecomputation:
	@staticmethod
	def compute_index():
		cache_index = {word: i for i, word in enumerate(ALLOWED_WORDS)}
		util.FileIO.write(PATH["index"], cache_index)

	@staticmethod
	def compute_frequency():
		cache_frequency = {word: dict(Counter(word)) for word in ALLOWED_WORDS}
		util.FileIO.write(PATH["frequency"], cache_frequency)

	@staticmethod
	def compute_state():
		cache_state = np.zeros(TOTALITY * TOTALITY, dtype=np.uint8)
		for (i, guess), (j, answer) in product(enumerate(ALLOWED_WORDS), enumerate(ALLOWED_WORDS)):
			cache_state[i * TOTALITY + j] = MyComputation.to_mask(guess, answer)
		cache_state.tofile(PATH["state"])

	@staticmethod
	@mu.Decorator.timing
	def compute_worst():
		tasks = ((guess, ALLOWED_WORDS, CACHE, TOTALITY) for guess in ALLOWED_WORDS)
		cache_worst = dict(POOL.imap_unordered(MyPrecomputation._compute_worst, tasks))
		util.FileIO.write(PATH["worst"], cache_worst)

	@staticmethod
	def _compute_worst(args):
		guess, candidate, cache, totality = args
		candidate = MyComputation.to_candidate(guess, 0, candidate, cache, totality)
		best_guess = EntropyAlgorithm.infer(candidate, cache, totality, accelerate=True)
		print(guess, len(candidate), best_guess)
		return guess, best_guess


if __name__ == "__main__":
	_QSS = "font-family: 'nyt-franklin'; color: %s; background-color: %s;"
	_QSS_LABEL = _QSS
	_QSS_BUTTON = (
		"QPushButton {" + _QSS + " border-radius: 5px}"
		"QPushButton:hover {background-color: %s}"
		"QPushButton:pressed {background-color: %s}"
	)

	QSS_LABEL = {
		"non_text": _QSS_LABEL % ("black", "white") + " border: 2px solid rgb(211,214,218);",
		"text": _QSS_LABEL % ("black", "white") + " border: 2px solid rgb(135,138,140);",
		"hint": _QSS_LABEL % ("rgb(181,184,188)", "white") + " border: 2px solid rgb(211,214,218);",
		"hit": _QSS_LABEL % ("rgb(200,0,0)", "white") + " border: 2px solid rgb(200,0,0);",
		"0": _QSS_LABEL % ("white", "rgb(120,124,126)"),
		"1": _QSS_LABEL % ("white", "rgb(198,180,86)"),
		"2": _QSS_LABEL % ("white", "rgb(112,169,97)")
	}
	QSS_BUTTON = {
		None: _QSS_BUTTON % ("black", "rgb(211,214,218)", "rgb(181,184,188)", "rgb(151,154,158)"),
		"0": _QSS_BUTTON % ("white", "rgb(120,124,126)", "rgb(90,94,96)", "rgb(60,64,66)"),
		"1": _QSS_BUTTON % ("white", "rgb(198,180,86)", "rgb(168,150,56)", "rgb(138,120,26)"),
		"2": _QSS_BUTTON % ("white", "rgb(112,169,97)", "rgb(82,139,67)", "rgb(52,109,37)")
	}

	_FONT_FAMILY = QFont().family()
	FONT_LABEL = QFont(_FONT_FAMILY, 21, QFont.Weight.Bold)
	FONT_TEXT = QFont(_FONT_FAMILY, 14, QFont.Weight.Bold)
	FONT_ENTER = QFont(_FONT_FAMILY, 12, QFont.Weight.Bold)
	FONT_DELETE = QFont(_FONT_FAMILY, 13, QFont.Weight.Bold)

	KEY = {getattr(Qt.Key, f"Key_{c.upper()}"): c for c in string.ascii_lowercase}
	KEY.update({Qt.Key.Key_Return: "enter", Qt.Key.Key_Backspace: "delete"})

	ALLOWED_WORDS = tuple(util.FileIO.read(util.join_path(util.RESOURCE, "wordle", "allowed_words.txt")).splitlines())
	POSSIBLE_WORDS = tuple(util.FileIO.read(util.join_path(util.RESOURCE, "wordle", "possible_words.txt")).splitlines())

	PATH = {
		"index": util.join_path(util.RESOURCE, "wordle", "cache_index.pkl"),
		"frequency": util.join_path(util.RESOURCE, "wordle", "cache_frequency.pkl"),
		"state": util.join_path(util.RESOURCE, "wordle", "cache_state.bin"),
		"worst": util.join_path(util.RESOURCE, "wordle", "cache_worst.pkl")
	}
	CACHE = {
		"index": util.FileIO.read(PATH["index"]) if os.path.exists(PATH["index"]) else None,
		"frequency": util.FileIO.read(PATH["frequency"]) if os.path.exists(PATH["frequency"]) else None,
		"state": np.fromfile(PATH["state"], dtype=np.uint8) if os.path.exists(PATH["state"]) else None,
		"worst": util.FileIO.read(PATH["worst"]) if os.path.exists(PATH["worst"]) else None
	}

	POOL = Pool(processes=cpu_count())
	TOTALITY = len(ALLOWED_WORDS)

	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
