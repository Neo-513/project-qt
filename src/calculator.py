from calculator_ui import Ui_MainWindow
from PyQt6.QtWidgets import QApplication, QMainWindow
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


class MyCore(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../calculator/calculator"))

		self.plainTextEdit.textChanged.connect(self.calculation)

	def calculation(self):
		equation = self.plainTextEdit.toPlainText().strip()
		if not equation:
			return self.label.clear()

		try:
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
					stack.append(self.calculate(elems))
				elif element:
					stack.append(element)

			if len(stack) != 1:
				return self.label.clear()
			self.label.setText(str(float(stack[0])).rstrip("0").rstrip("."))
		except:
			return self.label.clear()

	def calculate(self, elems):
		for opers in (("^", "%"), ("*", "/"), ("+", "-")):
			if any(oper in elems for oper in opers):
				elems = self.operate(elems, opers)
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
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
