from database_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QComboBox, QHeaderView, QLineEdit, QMainWindow, QRadioButton, QTableWidgetItem
import os
import sys
import webbrowser
import util


class MyCore(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../database/logo"))

		util.button(self.pushButton_add, lambda: MyOperate.add(self), "add")
		util.button(self.pushButton_delete, lambda: MyOperate.delete(self), "delete")
		util.button(self.pushButton_save, lambda: MyOperate.save(self), "save")
		util.select_folder(self.lineEdit_file, None, self.scan)
		util.Menu.menu(self.tableWidget, func=self.hyperlink)
		self.lineEdit_search.textChanged.connect(self.search)
		self.tableWidget.itemChanged.connect(self.editing)
		self.lineEdit_file.setVisible(False)

		if os.path.exists("database.json"):
			file = util.FileIO.read("database.json")
			for name, config in file.items():
				radio = QRadioButton(name)
				radio.setCursor(Qt.CursorShape.PointingHandCursor)
				radio.setVisible(False)
				radio.config = config
				util.cast(radio).clicked.connect(self.switch)
				self.horizontalLayout_config.addWidget(radio)
				radio.click() if len(file) == 1 else None

	def switch(self):
		config = util.cast(self.sender()).config
		self.lineEdit_file.setText(config["@path"])
		self.tableWidget.sort = config.get("@sort", [])

		headers = tuple(header for header in config if not header.startswith("@"))
		self.tableWidget.setColumnCount(len(headers))
		self.tableWidget.setHorizontalHeaderLabels(headers)

		self.tableWidget.config = []
		for header in headers:
			if not config[header]:
				self.tableWidget.config.append(None)
			elif config[header] == "*" or "%s" in config[header]:
				self.tableWidget.config.append(config[header])
			else:
				self.tableWidget.config.append([""] + config[header].split(","))
		self.scan()

	def scan(self):
		self.lineEdit_search.clear()

		file_path = self.lineEdit_file.text()
		if not os.path.exists(file_path):
			return

		datas = [[k] + v for k, v in util.FileIO.read(file_path).items()]
		datas.sort(key=lambda x: [x[i] for i in self.tableWidget.sort])

		MyDisplayer.display(self.tableWidget, self.editing, False)
		self.tableWidget.setRowCount(0)
		self.tableWidget.setRowCount(len(datas))
		self.statusbar.showMessage(f"共{self.tableWidget.rowCount()}条")
		for r, data in enumerate(datas):
			MyDisplayer.row(r, data, self.tableWidget, self.editing)
			self.tableWidget.item(r, 0).status = "Q"
			self.tableWidget.item(r, 0).setIcon(util.icon("../database/lock"))
			self.tableWidget.item(r, 0).setFlags(~Qt.ItemFlag.ItemIsEditable)
		MyDisplayer.display(self.tableWidget, self.editing, True)

	def search(self):
		keyword = self.lineEdit_search.text().strip()
		MyDisplayer.display(self.tableWidget, self.editing, False)
		if not keyword:
			for r in range(self.tableWidget.rowCount()):
				self.tableWidget.setRowHidden(r, False)
		else:
			for r in reversed(range(self.tableWidget.rowCount())):
				hidden = True
				for c in range(self.tableWidget.columnCount()):
					if self.tableWidget.item(r, c):
						text = self.tableWidget.item(r, c).text()
					elif isinstance(self.tableWidget.cellWidget(r, c), QLineEdit):
						text = self.tableWidget.cellWidget(r, c).text()
					elif isinstance(self.tableWidget.cellWidget(r, c), QComboBox):
						text = self.tableWidget.cellWidget(r, c).currentText()
					else:
						text = ""
					if keyword in text:
						hidden = False
						break
				self.tableWidget.setRowHidden(r, hidden)
		MyDisplayer.display(self.tableWidget, self.editing, True)

	def hyperlink(self, widget, point):
		item = widget.itemAt(point)
		text = item.text().strip()
		url = self.tableWidget.config[item.column()]
		if text and url:
			util.Menu.add(widget.property("menu"), "../database/link", "超链接", lambda: webbrowser.open(url % text))

	def editing(self):
		r = self.tableWidget.currentRow()
		if not 0 <= r < self.tableWidget.rowCount():
			return
		if self.tableWidget.item(r, 0).status == "Q":
			self.tableWidget.itemChanged.disconnect(self.editing)
			self.tableWidget.item(r, 0).status = "U"
			self.tableWidget.item(r, 0).setIcon(util.icon("edit"))
			self.tableWidget.itemChanged.connect(self.editing)

	def enterEvent(self, event):
		if self.rect().bottom() - event.position().toPoint().y() >= 30:
			return
		for i in range(self.horizontalLayout_config.count()):
			widget = self.horizontalLayout_config.itemAt(i).widget()
			widget.setVisible(True) if widget else None

	def leaveEvent(self, a0):
		for i in range(self.horizontalLayout_config.count()):
			widget = self.horizontalLayout_config.itemAt(i).widget()
			widget.setVisible(False) if widget else None


class MyOperate:
	@staticmethod
	def add(self):
		if not self.tableWidget.columnCount():
			return

		MyDisplayer.display(self.tableWidget, self.editing, False)
		self.tableWidget.insertRow(0)
		MyDisplayer.row(0, "", self.tableWidget, self.editing)
		self.tableWidget.item(0, 0).status = "I"
		self.tableWidget.item(0, 0).setIcon(util.icon("add"))
		self.tableWidget.verticalScrollBar().setValue(0)
		MyDisplayer.display(self.tableWidget, self.editing, True)

	@staticmethod
	def delete(self):
		if not self.tableWidget.columnCount():
			return

		MyDisplayer.display(self.tableWidget, self.editing, False)
		for r in set(item.row() for item in self.tableWidget.selectedItems()):
			if self.tableWidget.item(r, 0).status != "I":
				self.tableWidget.item(r, 0).status = "D"
				self.tableWidget.item(r, 0).setIcon(util.icon("delete"))
		MyDisplayer.display(self.tableWidget, self.editing, True)

	@staticmethod
	def save(self):
		if not self.tableWidget.columnCount():
			return

		file_path = self.lineEdit_file.text()
		if not os.path.exists(file_path):
			return

		dic, flag = util.FileIO.read(file_path), False
		for r in range(self.tableWidget.rowCount()):
			status = self.tableWidget.item(r, 0).status
			pk = self.tableWidget.item(r, 0).text()

			data = []
			for c in range(1, self.tableWidget.columnCount()):
				if isinstance(self.tableWidget.config[c], list):
					data.append(self.tableWidget.cellWidget(r, c).currentText())
				elif self.tableWidget.config[c] == "*":
					data.append(self.tableWidget.cellWidget(r, c).text())
				else:
					data.append(self.tableWidget.item(r, c).text())
			data += dic.get(pk, [])[self.tableWidget.columnCount() - 1:]

			if status == "I":
				if not pk:
					return util.dialog("主键不可为空!", "error")
				if pk in dic:
					return util.dialog(f"主键[{pk}]已存在!", "error")
				dic[pk] = data
				flag = True
			elif status == "U":
				dic[pk] = data
				flag = True
			elif status == "D":
				if pk in dic:
					dic.pop(pk)
					flag = True

		if flag:
			util.FileIO.write(file_path, dic)
			util.dialog("保存成功!", "success")
		self.scan()


class MyDisplayer:
	@staticmethod
	def display(table_widget, func, enable):
		table_widget.setUpdatesEnabled(enable)
		if enable:
			table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
			table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
			table_widget.itemChanged.connect(func)
			table_widget.update()
		else:
			table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
			table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
			table_widget.itemChanged.disconnect(func)

	@staticmethod
	def row(r, data, table_widget, func):
		for c in range(table_widget.columnCount()):
			text = data[c] if data and c < len(data) else ""
			if isinstance(table_widget.config[c], list):
				widget = QComboBox()
				widget.addItems(table_widget.config[c])
				widget.setCurrentText(text)
				widget.setMaxVisibleItems(widget.count())
				util.cast(widget).currentTextChanged.connect(func)
				table_widget.setCellWidget(r, c, widget)
			elif table_widget.config[c] == "*":
				widget = QLineEdit(text)
				widget.setStyleSheet("border: none")
				MyPwd.pwd(widget) if data else None
				util.cast(widget).textChanged.connect(func)
				table_widget.setCellWidget(r, c, widget)
			else:
				table_widget.setItem(r, c, QTableWidgetItem(text))


class MyPwd:
	@staticmethod
	def pwd(line_edit):
		position = QLineEdit.ActionPosition.LeadingPosition
		util.add_action(line_edit, "../database/hide", "密码", lambda: MyPwd._switch(line_edit), position=position)
		line_edit.setEchoMode(QLineEdit.EchoMode.Password)
		line_edit.setReadOnly(True)

	@staticmethod
	def _switch(line_edit):
		if line_edit.echoMode() == QLineEdit.EchoMode.Normal:
			line_edit.setEchoMode(QLineEdit.EchoMode.Password)
			line_edit.setReadOnly(True)
			line_edit.actions()[0].setIcon(util.icon("../database/hide"))
		else:
			line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
			line_edit.setReadOnly(False)
			line_edit.actions()[0].setIcon(util.icon("../database/show"))


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
