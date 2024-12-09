from calculator_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow
import pyperclip
import re
import sys
import util

REGEX = re.compile("([+*/^%()\\-])")
REPLACEMENT = {" ": "", "\n": "", "\t": "", "（": "(", "）": ")", "(-": "(0-"}
OPERATION = {
	"+": lambda passive_num, active_num: passive_num + active_num,
	"-": lambda passive_num, active_num: passive_num - active_num,
	"*": lambda passive_num, active_num: passive_num * active_num,
	"/": lambda passive_num, active_num: passive_num / active_num,
	"^": lambda passive_num, active_num: passive_num ** active_num,
	"%": lambda passive_num, active_num: passive_num % active_num
}


class QtCore(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../calculator/calculator"))

		self.plainTextEdit.textChanged.connect(self.calculation)

	def calculation(self):
		try:
			equation = self.plainTextEdit.toPlainText().strip()
			if not equation:
				raise Exception

			equation = f"({equation})"
			for k, v in REPLACEMENT.items():
				equation = equation.replace(k, v)

			stack = []
			for element in REGEX.split(equation):
				if element == ")":
					elems = []
					while stack[-1] != "(":
						elems.insert(0, stack.pop())
					stack.pop()
					stack.append(QtStatic.calculate(elems))
				elif element:
					stack.append(element)

			if len(stack) != 1:
				raise Exception
			self.statusbar.showMessage(f"计算结果: {str(float(stack[0])).rstrip('0').rstrip('.')}")
		except:
			self.statusbar.clearMessage()

	def keyPressEvent(self, event):
		if event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
			result = self.statusbar.currentMessage().lstrip("计算结果: ")
			pyperclip.copy(result) if result else None


class QtStatic:
	@staticmethod
	def calculate(elems):
		for opers in (("^", "%"), ("*", "/"), ("+", "-")):
			if any(oper in elems for oper in opers):
				elems = QtStatic.operate(elems, opers)
		if len(elems) == 1:
			return elems[0]

	@staticmethod
	def operate(elems, opers):
		stack = [elems[0]]
		for elem in elems[1:]:
			if stack[-1] in opers:
				operation = None if not stack else stack.pop()
				stack[-1] = OPERATION[operation](float(stack[-1]), float(elem))
			else:
				stack.append(elem)
		return stack


if __name__ == "__main__":
	app = QApplication(sys.argv)
	qt_core = QtCore()
	qt_core.show()
	sys.exit(app.exec())
