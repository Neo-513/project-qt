from PyQt6.QtCore import QDir, QPoint, Qt, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QIcon, QPixmap
from PyQt6.QtWidgets import QComboBox, QFileDialog, QLineEdit, QListWidget, QMenu, QMessageBox, QPushButton
from PyQt6.QtWidgets import QTableWidget, QTextBrowser, QTreeWidget, QTreeWidgetItem
from typing import Any
import json
import os
import pickle
import re
import shutil
import subprocess
import sys

DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop").replace("\\", "/")
RESOURCE = os.path.join(getattr(sys, "_MEIPASS", os.path.abspath("..")), "assets").replace("\\", "/")
BANNED_CHAR = re.compile(r'[\\/*?:"<>|]')


file_icons = {
	".jpeg": "image",
	".jpg": "image",
	".m4s": "video",
	".mp3": "audio",
	".mp4": "video",
	".png": "image",
}


def cast(obj):
	return obj


def icon(path: str) -> QIcon:
	return QIcon(QPixmap(os.path.join(RESOURCE, "global", f"{path}.png").replace("\\", "/")))


def cmd(commands: str):
	subprocess.run(commands, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def search(line_edit: QLineEdit, widget: QListWidget | QTableWidget, show_check=True, do_search=False):
	def _func():
		keyword = line_edit.text().strip()
		if isinstance(widget, QListWidget):
			for i in range(widget.count()):
				widget.item(i).setHidden(keyword not in widget.item(i).text())
				if show_check:
					widget.item(i).setCheckState(Qt.CheckState.Unchecked)
		elif isinstance(widget, QTableWidget):
			widget.setUpdatesEnabled(False)
			for r in reversed(range(widget.rowCount())):
				if not keyword:
					widget.setRowHidden(r, False)
					continue

				hidden = True
				for c in range(widget.columnCount()):
					text, table_item, table_widget = "", widget.item(r, c), widget.cellWidget(r, c)
					if table_item:
						text = table_item.text()
					elif table_widget and isinstance(table_widget, QLineEdit):
						text = table_widget.text()
					elif table_widget and isinstance(table_widget, QComboBox):
						text = table_widget.currentText()
					if keyword in text:
						hidden = False
						break
				widget.setRowHidden(r, hidden)
			widget.setUpdatesEnabled(True)
			widget.update()

	if do_search:
		_func()
	else:
		add_action(line_edit, "clear", "清空", line_edit.clear)
		cast(line_edit).textChanged.connect(_func)


def dialog(msg: str, msg_type: str) -> bool | None:
	message_box = QMessageBox()
	message_box.setText(msg)
	message_box.setWindowIcon(icon(msg_type))
	message_box.setWindowTitle(" ")

	if msg_type == "warning":
		message_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
	return message_box.exec() == QMessageBox.StandardButton.Yes


def button(push_button: QPushButton, func: callable, ico: str = None, tip: str = None):
	cast(push_button).clicked.connect(func)
	push_button.setIcon(icon(ico)) if ico else None
	push_button.setToolTip(tip) if tip else None
	push_button.setCursor(Qt.CursorShape.PointingHandCursor)


def add_action(widget: Any, ico: str, text: str, func: callable, at_end=True):
	if isinstance(widget, QMenu):
		action = QAction(text, widget)
		widget.addAction(action)
	else:
		action = QAction(widget)
		action.setToolTip(text)
	action.setIcon(icon(ico))
	cast(action).triggered.connect(func)

	if isinstance(widget, QLineEdit):
		if at_end:
			widget.addAction(action, QLineEdit.ActionPosition.TrailingPosition)
		else:
			widget.addAction(action, QLineEdit.ActionPosition.LeadingPosition)


def select_folder(line_edit: QLineEdit, push_button: QPushButton, func: callable, clean=False, clear=False):
	def _select():
		folder_path = QFileDialog.getExistingDirectory(directory=line_edit.text())
		if not os.path.exists(folder_path):
			return
		line_edit.setText(folder_path)
		func() if func else None

	def _clean():
		folder_path = line_edit.text()
		if not os.path.exists(folder_path):
			return
		if not os.listdir(folder_path):
			return dialog(f"路径[{folder_path}]下没有可清理文件!", "error")
		if dialog(f"确认清理路径[{folder_path}]下所有文件?", "warning"):
			shutil.rmtree(folder_path)
			os.mkdir(folder_path)
			dialog("清理完成!", "success")
		func() if func else None

	add_action(line_edit, "open_folder", "打开文件夹", lambda: FileIO.open_folder(line_edit.text()))
	add_action(line_edit, "clean", "清理文件", _clean) if clean else None
	add_action(line_edit, "clear", "清空", line_edit.clear) if clear else None
	button(push_button, _select, "folder") if push_button else None
	line_edit.setReadOnly(True)
	line_edit.setToolTip(line_edit.placeholderText())


def select_file(line_edit: QLineEdit, push_button: QPushButton, flt: list, func=None, select=False):
	def _select():
		f = ";".join([f"{f} (*.{f})" for f in flt])
		file_path = QFileDialog.getOpenFileName(directory=os.path.dirname(line_edit.text()), filter=f)[0]
		if not file_path:
			return
		line_edit.setText(file_path)
		func() if func else None

	add_action(line_edit, "open_folder", "打开文件夹", lambda: FileIO.open_folder(line_edit.text()))
	add_action(line_edit, "select_file", "选择文件", _select) if select else None
	button(push_button, _select, "file") if push_button else None
	line_edit.setReadOnly(True)
	line_edit.setToolTip(line_edit.placeholderText())


def pwd(line_edit: QLineEdit):
	def _func():
		if line_edit.echoMode() == QLineEdit.EchoMode.Normal:
			line_edit.setEchoMode(QLineEdit.EchoMode.Password)
			line_edit.setReadOnly(True)
			line_edit.actions()[0].setIcon(icon("hide"))
		else:
			line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
			line_edit.setReadOnly(False)
			line_edit.actions()[0].setIcon(icon("show"))

	add_action(line_edit, "hide", "密码", _func, at_end=False)
	line_edit.setEchoMode(QLineEdit.EchoMode.Password)
	line_edit.setReadOnly(True)


class FileIO:
	@staticmethod
	def read(file_path):
		file_type = os.path.splitext(file_path)[1]
		encoding = "utf-8"

		if file_type == ".pkl":
			with open(file_path, mode="rb") as file:
				return pickle.load(file)
		elif file_type == ".json":
			with open(file_path, mode="r", encoding=encoding) as file:
				return json.load(file)
		else:
			with open(file_path, mode="r", encoding=encoding) as file:
				return file.read()

	@staticmethod
	def write(file_path, datas):
		file_type = os.path.splitext(file_path)[1]
		encoding = "utf-8"

		if file_type == ".pkl":
			with open(file_path, mode="wb") as file:
				pickle.dump(datas, file)
		elif file_type == ".json":
			with open(file_path, mode="w", encoding=encoding) as file:
				json.dump(datas, file)
		else:
			with open(file_path, mode="w", encoding=encoding) as file:
				file.write(datas)

	@staticmethod
	def open_folder(folder_path):
		if not os.path.exists(folder_path):
			return
		if os.path.isfile(folder_path):
			folder_path = os.path.dirname(folder_path)
		QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

	@staticmethod
	def open_file(file_path):
		if not os.path.exists(file_path):
			return
		if os.path.isfile(file_path):
			QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))


class Tree:
	@staticmethod
	def scan(tree_widget: QTreeWidget, folder_path: str) -> None:
		def _func(path_parent, parent):
			entry = QDir(path_parent).entryList(QDir.Filter.Dirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)
			entry.sort(key=lambda x: tuple(reversed(os.path.splitext(x))))

			for name in entry:
				path_child = os.path.join(path_parent, name).replace("\\", "/")
				if os.path.isdir(path_child):
					ico = "folder"
				else:
					file_type = os.path.splitext(path_child)[1].lower()
					ico = file_icons.get(file_type, "file")

				child = QTreeWidgetItem([name])
				child.setText(0, name)
				child.setIcon(0, icon(ico))
				child.setToolTip(0, path_child)
				parent.addChild(child) if parent else tree_widget.addTopLevelItem(child)
				_func(path_child, child) if ico == "folder" else None

		tree_widget.clear()
		if os.path.exists(folder_path):
			_func(folder_path, None)

	@staticmethod
	def sync_check(tree_widget: QTreeWidget) -> None:
		def _func(item):
			cast(tree_widget).itemChanged.disconnect(_func)
			if item.data(0, Qt.ItemDataRole.UserRole):
				for i in range(item.childCount()):
					item.child(i).setCheckState(0, item.checkState(0))
			else:
				parent = item.parent()
				if parent:
					count = sum([parent.child(i).checkState(0) == Qt.CheckState.Checked for i in range(parent.childCount())])
					if count == 0:
						parent.setCheckState(0, Qt.CheckState.Unchecked)
					elif count == parent.childCount():
						parent.setCheckState(0, Qt.CheckState.Checked)
					else:
						parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
			cast(tree_widget.itemChanged).connect(_func)

		cast(tree_widget.itemChanged).connect(_func)


class Menu:
	@staticmethod
	def menu(self: Any, widget: QListWidget | QTreeWidget, func: callable) -> None:
		def _func(point):
			self.qu_menu.clear()
			func(widget, point, self.qu_menu)
			self.qu_menu.exec(widget.viewport().mapToGlobal(point))

		widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		cast(widget).customContextMenuRequested.connect(lambda point: _func(point))
		self.qu_menu = QMenu(widget)

	@staticmethod
	def add_menu(widget: QTreeWidget | QListWidget, point: QPoint, qu_menu: QMenu, name, ico, func, rely=True, effective=True):
		if not effective:
			return
		item = widget.itemAt(point)
		if rely and not item:
			return
		add_action(qu_menu, ico, name, func)
		widget.setCurrentItem(item) if rely and item else None

	@staticmethod
	def open_folder(widget: QTreeWidget | QListWidget) -> Any:
		if isinstance(widget, QTreeWidget):
			FileIO.open_folder(widget.currentItem().toolTip(0))
		elif isinstance(widget, QListWidget):
			FileIO.open_folder(widget.currentItem().toolTip())

	@staticmethod
	def open_file(widget: QTreeWidget | QListWidget) -> Any:
		if isinstance(widget, QTreeWidget):
			FileIO.open_file(widget.currentItem().toolTip(0))
		elif isinstance(widget, QListWidget):
			FileIO.open_file(widget.currentItem().toolTip())

	@staticmethod
	def select_all(widget: QTreeWidget | QListWidget) -> Any:
		if isinstance(widget, QTreeWidget):
			for i in range(widget.topLevelItemCount()):
				widget.topLevelItem(i).setCheckState(0, Qt.CheckState.Checked)
		elif isinstance(widget, QListWidget):
			for i in range(widget.count()):
				widget.item(i).setCheckState(Qt.CheckState.Checked)

	@staticmethod
	def unselect_all(widget: QTreeWidget | QListWidget) -> Any:
		if isinstance(widget, QTreeWidget):
			for i in range(widget.topLevelItemCount()):
				widget.topLevelItem(i).setCheckState(0, Qt.CheckState.Unchecked)
		elif isinstance(widget, QListWidget):
			for i in range(widget.count()):
				widget.item(i).setCheckState(Qt.CheckState.Unchecked)


class Sync:
	@staticmethod
	def scroll(self: Any, widget_old: QListWidget | QTextBrowser, widget_new: QListWidget | QTextBrowser) -> None:
		def _func():
			widget = self.sender()
			value = widget.value()
			widgets[widget].setValue(value)

		vbar_old, hbar_old = widget_old.verticalScrollBar(), widget_old.horizontalScrollBar()
		vbar_new, hbar_new = widget_new.verticalScrollBar(), widget_new.horizontalScrollBar()
		widgets = {vbar_old: vbar_new, hbar_old: hbar_new, vbar_new: vbar_old, hbar_new: hbar_old}

		cast(vbar_old).valueChanged.connect(_func)
		cast(vbar_new).valueChanged.connect(_func)
		cast(hbar_old).valueChanged.connect(_func)
		cast(hbar_new).valueChanged.connect(_func)

	@staticmethod
	def select(self: Any, widget_old: QListWidget, widget_new: QListWidget) -> None:
		def _func():
			widget = self.sender()
			widgets[widget].setCurrentRow(widget.currentRow())

		widgets = {widget_old: widget_new, widget_new: widget_old}
		cast(widget_old).itemSelectionChanged.connect(_func)
		cast(widget_new).itemSelectionChanged.connect(_func)
