from database_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QComboBox, QHeaderView, QMainWindow, QLineEdit, QRadioButton, QTableWidgetItem
import os
import sys
import webbrowser
import util

ICON = {"Q": "../database/lock", "I": "add", "U": "edit", "D": "delete"}


class MyCore(QMainWindow, Ui_MainWindow):
	config = None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../database/database"))

		util.button(self.pushButton_add, self.func_add, "add")
		util.button(self.pushButton_delete, self.func_delete, "delete")
		util.button(self.pushButton_save, self.func_save, "save")
		util.select_folder(self.lineEdit_file, None, self.scan)
		util.Menu.menu(self.tableWidget, func=self.menu)
		self.lineEdit_search.textChanged.connect(self.search)
		self.tableWidget.itemChanged.connect(self.editing)
		self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		self.tableWidget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		self.lineEdit_file.setVisible(False)

		if os.path.exists("database.json"):
			self.config = util.FileIO.read("database.json")
			for name in self.config:
				radio = QRadioButton(name)
				radio.setCursor(Qt.CursorShape.PointingHandCursor)
				radio.setVisible(False)
				util.cast(radio).clicked.connect(self.switch)
				self.horizontalLayout_config.addWidget(radio)
				radio.click() if len(self.config) == 1 else None

	def func_add(self):
		if self.tableWidget.columnCount():
			self.tableWidget.setUpdatesEnabled(False)
			self.tableWidget.insertRow(0)
			self.assign(0, "I")
			self.tableWidget.verticalScrollBar().setValue(0)
			self.tableWidget.setUpdatesEnabled(True)
			self.tableWidget.update()

	def func_delete(self):
		if self.tableWidget.columnCount():
			self.tableWidget.setUpdatesEnabled(False)
			for r in set(item.row() for item in self.tableWidget.selectedItems()):
				if self.tableWidget.item(r, 0).data(Qt.ItemDataRole.UserRole) != "I":
					self.change(r, "D")
			self.tableWidget.setUpdatesEnabled(True)
			self.tableWidget.update()

	def func_save(self):
		if not self.tableWidget.columnCount():
			return

		file_path = self.lineEdit_file.text()
		if not os.path.exists(file_path):
			return

		dic, flag = util.FileIO.read(file_path), False
		for r in range(self.tableWidget.rowCount()):
			status = self.tableWidget.item(r, 0).data(Qt.ItemDataRole.UserRole)
			pk = self.tableWidget.item(r, 0).text()

			data = []
			for c in range(1, self.tableWidget.columnCount()):
				item = self.tableWidget.horizontalHeaderItem(c)
				if item.data(Qt.ItemDataRole.UserRole) == "*":
					data.append(self.tableWidget.cellWidget(r, c).text())
				elif isinstance(item.data(Qt.ItemDataRole.UserRole), list):
					data.append(self.tableWidget.cellWidget(r, c).currentText())
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

	def assign(self, r, status, data=None):
		for c in range(self.tableWidget.columnCount()):
			item = self.tableWidget.horizontalHeaderItem(c)
			text = data[c] if data and c < len(data) else ""

			if item.data(Qt.ItemDataRole.UserRole) == "*":
				widget = QLineEdit(text)
				widget.setStyleSheet("border: none")
				util.pwd(widget) if data else None
				util.cast(widget).textChanged.connect(self.editing)
				self.tableWidget.setCellWidget(r, c, widget)
			elif isinstance(item.data(Qt.ItemDataRole.UserRole), list):
				widget = QComboBox()
				widget.addItems(item.data(Qt.ItemDataRole.UserRole))
				widget.setCurrentText(text)
				widget.setMaxVisibleItems(widget.count())
				util.cast(widget).currentTextChanged.connect(self.editing)
				self.tableWidget.setCellWidget(r, c, widget)
			else:
				self.tableWidget.setItem(r, c, QTableWidgetItem(text))

		self.change(r, status)
		self.tableWidget.item(r, 0).setFlags(~Qt.ItemFlag.ItemIsEditable) if data else None

	def switch(self):
		config = self.config[util.cast(self.sender()).text()]
		self.lineEdit_file.setText(config["@path"])

		headers = [header for header in config if not header.startswith("@")]
		self.tableWidget.setColumnCount(len(headers))
		self.tableWidget.setHorizontalHeaderLabels(headers)
		self.tableWidget.setProperty("sort", config.get("@sort", [0]))

		for i, header in enumerate(headers):
			item = self.tableWidget.horizontalHeaderItem(i)
			if not config[header]:
				item.setData(Qt.ItemDataRole.UserRole, None)
				item.setIcon(QIcon())
			elif config[header] == "*":
				item.setData(Qt.ItemDataRole.UserRole, "*")
				item.setIcon(util.icon("../database/secure"))
			elif "%s" in config[header]:
				item.setData(Qt.ItemDataRole.UserRole, config[header])
				item.setIcon(util.icon("internet"))
			else:
				item.setData(Qt.ItemDataRole.UserRole, [""] + config[header].split(","))
				item.setIcon(util.icon("list"))
		self.scan()

	def scan(self):
		self.lineEdit_search.clear()

		file_path = self.lineEdit_file.text()
		if not os.path.exists(file_path):
			return

		datas = [[k] + v for k, v in util.FileIO.read(file_path).items()]
		datas.sort(key=lambda x: [x[i] for i in self.tableWidget.property("sort")])

		self.tableWidget.setRowCount(0)
		self.tableWidget.setRowCount(len(datas))
		self.statusbar.showMessage(f"共{self.tableWidget.rowCount()}条")

		self.tableWidget.setUpdatesEnabled(False)
		for r, data in enumerate(datas):
			self.assign(r, "Q", data)
		self.tableWidget.setUpdatesEnabled(True)
		self.tableWidget.update()

	def editing(self):
		r = self.tableWidget.currentRow()
		if not (0 <= r < self.tableWidget.rowCount()):
			return
		if self.tableWidget.item(r, 0).data(Qt.ItemDataRole.UserRole) in ("Q", "U"):
			self.change(r, "U")

	def change(self, r, status):
		self.tableWidget.itemChanged.disconnect(self.editing)
		self.tableWidget.item(r, 0).setData(Qt.ItemDataRole.UserRole, status)
		self.tableWidget.item(r, 0).setIcon(util.icon(ICON[status]))
		self.tableWidget.itemChanged.connect(self.editing)

	def search(self):
		keyword = self.lineEdit_search.text().strip()
		self.tableWidget.setUpdatesEnabled(False)
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
		self.tableWidget.setUpdatesEnabled(True)
		self.tableWidget.update()

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

	def menu(self, widget, point):
		item = widget.itemAt(point)
		text = item.text().strip()
		url = self.tableWidget.horizontalHeaderItem(item.column()).data(Qt.ItemDataRole.UserRole)
		if text and url:
			util.Menu.add(widget.property("menu"), "../database/arrow", "超链接", lambda: webbrowser.open(url % text))


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
