from PyQt6.QtCore import QDir
from PyQt6.QtWidgets import QApplication, QMainWindow
from packer_ui import Ui_MainWindow
import os
import sys
import util


class MyCore(QMainWindow, Ui_MainWindow):
	COMMAND = {
		"exe": ("pyinstaller -w -F src/%.py\n--distpath build --specpath build --workpath build\n"
			"--icon=../static/%/logo.png\n--add-data=../static/common;static/common\n--add-data=../static/%;static/%"),
		"ui": "python -m PyQt6.uic.pyuic src/%_ui.ui -o src/%_ui.py"
	}

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../packer/logo"))

		util.select_folder(self.lineEdit, self.pushButton_select, self.scan)
		util.button(self.pushButton_pack, self.pack, "export")
		util.console(self.plainTextEdit_console)
		self.radioButton_exe.clicked.connect(self.command)
		self.radioButton_ui.clicked.connect(self.command)
		self.comboBox.currentTextChanged.connect(self.command)

		self.process = util.process(self.process_log, self.process_finished)
		if os.path.exists("config.json"):
			config = util.read("config.json")["packer"]
			self.lineEdit.setText(config["path"]) if os.path.exists(config["path"]) else None
		self.scan()

	def scan(self):
		self.comboBox.clear()
		self.plainTextEdit_command.clear()
		self.plainTextEdit_console.clear()

		for file in QDir(f"{self.lineEdit.text()}/src").entryList(["*_ui.ui"], QDir.Filter.Files, QDir.SortFlag.Name):
			self.comboBox.addItem(util.icon(f"{self.lineEdit.text()}/static/{file[:-6]}/logo", absolute=True), file[:-6])
		self.comboBox.insertItem(0, "") if self.comboBox.count() else None
		self.comboBox.setCurrentText("")
		self.comboBox.setMaxVisibleItems(self.comboBox.count())

	def pack(self):
		if not self.plainTextEdit_command.toPlainText():
			return
		util.export(self.pushButton_pack, False)
		util.console(self.plainTextEdit_console)
		self.process.setWorkingDirectory(self.lineEdit.text())
		self.process.start("cmd", ["/c"] + self.plainTextEdit_command.toPlainText().replace("\n", " ").split(" "))

	def command(self):
		file = self.comboBox.currentText()
		if not file:
			return self.plainTextEdit_command.clear()
		command = self.COMMAND["exe" if self.radioButton_exe.isChecked() else "ui"]
		self.plainTextEdit_command.setPlainText(command.replace("%", file))

	def process_log(self):
		self.plainTextEdit_console.appendPlainText(self.process.readAllStandardError().data().decode("gbk").strip())
		self.plainTextEdit_console.verticalScrollBar().setValue(self.plainTextEdit_console.verticalScrollBar().maximum())

	def process_finished(self, exit_code):
		util.export(self.pushButton_pack, True)
		if exit_code == 0:
			util.dialog("打包完成!", "success")
		else:
			util.console(self.plainTextEdit_console, alert=True)


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
