from json_formatter_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow
import json
import sys
import util

COLOR_RED = "rgb(163,21,21)"
COLOR_BLUE = "rgb(4,81,165)"
COLOR_GREEN = "rgb(9,134,88)"


class MyCore(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../json_formatter/json"))

	def keyPressEvent(self, a0):
		if a0.key() != Qt.Key.Key_F4:
			return

		try:
			jsn = json.loads(self.textEdit.toPlainText())
			if isinstance(jsn, dict):
				jsn = dict(sorted(jsn.items()))
		except:
			return self.textEdit.setHtml(self.textEdit.toPlainText().replace("\n", "<br>").replace(" ", "&nbsp;"))

		htmls = []
		html = '<span style="color: %s">%s</span>%s'
		for i, line in enumerate(json.dumps(jsn, indent=4, ensure_ascii=False).splitlines()):
			comma = "," if line[-1] == "," else ""
			line = line.strip(",").replace('\\"', "\\&quot;")

			if line.strip() in ("{", "}", "[", "]", "{}", "[]"):
				htmls.append(line.replace(" ", "&nbsp;") + comma)
				continue
			if line[-3:] in (": {", ": [") or line[-4:] in (": {}", ": []"):
				pos = line.rfind(":")
				text = line[:pos].replace(" ", "&nbsp;")
				htmls.append(html % (COLOR_RED, text, line[pos:] + comma))
				continue
			if '"' not in line or (line.count('"') == 2 and '"' not in line.strip()[1:-1]):
				text = line.replace(" ", "&nbsp;")
				color = COLOR_BLUE if '"' in line else COLOR_GREEN
				htmls.append(html % (color, text, comma))
				continue

			pos = line.strip()[1:].find('"') + (len(line) - len(line.strip()) + 2)
			color = COLOR_BLUE if line.endswith('"') else COLOR_GREEN
			text_key = line[:pos].replace(" ", "&nbsp;")
			text_value = line[pos + 2:].replace(" ", "&nbsp;")
			htmls.append(html % (COLOR_RED, text_key, ": ") + html % (color, text_value, comma))
		self.textEdit.setHtml("<br>".join(htmls))


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
