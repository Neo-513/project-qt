from differ_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow
import difflib
import re
import sys
import util

DIFF = difflib.HtmlDiff()
REGEX = re.compile("<a .+?</a>")
SPAN = ('<span class="diff_add">', '<span class="diff_sub">', '<span class="diff_chg">')
CSS = (
	"<style>"
	".diff_add { background-color: #aaffaa }"
	".diff_sub { background-color: #ffaaaa }"
	".diff_chg { background-color: #ffff77 }"
	".diff_header { background-color:#e0e0e0; text-align:right }"
	".diff_prompt { background-color:#aabbcc; text-align:right }"
	"</style>"
)


class MyCore(QMainWindow, Ui_MainWindow):
	text_old, text_new = None, None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../differ/differ"))

		util.Sync.scroll(self, self.plainTextEdit_old, self.plainTextEdit_new)
		util.Sync.scroll(self, self.textBrowser_old, self.textBrowser_new)

		self.textBrowser_old.hide()
		self.textBrowser_new.hide()
		self.statusbar.showMessage("按 F4 比对")

	def keyPressEvent(self, event):
		if event.key() != Qt.Key.Key_F4:
			return
		for widget in (self.plainTextEdit_old, self.plainTextEdit_new, self.textBrowser_old, self.textBrowser_new):
			widget.setVisible(not widget.isVisible())
		if self.plainTextEdit_old.isVisible():
			return self.plainTextEdit_old.setFocus()

		text_old = self.plainTextEdit_old.toPlainText()
		text_new = self.plainTextEdit_new.toPlainText()

		if text_old == self.text_old and text_new == self.text_new:
			return
		self.text_old, self.text_new = text_old, text_new

		if not text_old and not text_new:
			self.textBrowser_old.clear()
			self.textBrowser_new.clear()
			return

		table = DIFF.make_table(text_old.splitlines(keepends=True), text_new.splitlines(keepends=True))
		html_old, html_new = [CSS], [CSS]

		for i, line in enumerate(table.splitlines()):
			line = REGEX.sub("", line)
			html_old.append(line)
			html_new.append(line)

			if line.strip().startswith("<tr>"):
				html_old[-1], html_new[-1] = line.split('</td><td class="diff_next">')
				html_old[-1] = f"{html_old[-1]}</td></tr>"
				html_new[-1] = f'<tr><td class="diff_next">{html_new[-1]}'

				for span in SPAN:
					if span in html_old[-1] or span in html_new[-1]:
						html_old[-1] = html_old[-1].replace("diff_header", "diff_prompt", 1)
						html_new[-1] = html_new[-1].replace("diff_header", "diff_prompt", 1)
						break

		self.textBrowser_old.setHtml("\n".join(html_old))
		self.textBrowser_new.setHtml("\n".join(html_new))


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
