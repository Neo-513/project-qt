from toggle_case_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QApplication, QMainWindow
import sys
import util


class MyCore(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../toggle_case/toggle_case"))

	def keyPressEvent(self, a0):
		if a0.key() != Qt.Key.Key_F4:
			return

		cursor = self.plainTextEdit.textCursor()
		text = self.plainTextEdit.toPlainText()

		selected_text = cursor.selectedText()
		start = cursor.selectionStart()
		end = cursor.selectionEnd()

		if selected_text:
			self.plainTextEdit.setPlainText(text[:start] + self.toggle(selected_text) + text[end:])
			cursor.setPosition(start)
			cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
			self.plainTextEdit.setTextCursor(cursor)
		else:
			self.plainTextEdit.setPlainText(self.toggle(text))
			cursor.setPosition(end)
			self.plainTextEdit.setTextCursor(cursor)

	@staticmethod
	def toggle(text):
		return text.lower() if text.isupper() else text.upper()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
