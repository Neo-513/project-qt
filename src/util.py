from PyQt6.QtCore import QDir, Qt, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QIcon
from PyQt6.QtWidgets import QFileDialog, QLineEdit, QListWidget, QMenu, QMessageBox, QPushButton
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
import json
import os
import pickle
import re
import shutil
import sys

DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop").replace("\\", "/")
RESOURCE = os.path.join(getattr(sys, "_MEIPASS", os.path.abspath("..")), "assets").replace("\\", "/")
BANNED_CHAR = re.compile(r'[\\/*?:"<>|]')


def cast(obj):
	return obj


def join_path(*paths):
	return os.path.join("", *paths).replace("\\", "/")


def icon(path: str) -> QIcon:
	return QIcon(join_path(RESOURCE, "global", f"{path}.png"))


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


def add_action(line_edit: QLineEdit, ico: str, text: str, func: callable, position: QLineEdit.ActionPosition = QLineEdit.ActionPosition.TrailingPosition):
	action = QAction(line_edit)
	action.setIcon(icon(ico))
	action.setToolTip(text)
	cast(action).triggered.connect(func)
	line_edit.addAction(action, position)


def select_folder(line_edit: QLineEdit, push_button: QPushButton, func: callable, clean=False):
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
		if dialog(f"确认清理路径[{folder_path}]下所有文件?", "warning"):
			shutil.rmtree(folder_path)
			os.mkdir(folder_path)
			dialog("清理完成!", "success")
		func() if func else None

	add_action(line_edit, "open_folder", "打开文件夹", lambda: open_folder(line_edit.text()))
	add_action(line_edit, "clean", "清理文件", _clean) if clean else None
	button(push_button, _select, "folder") if push_button else None
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

	add_action(line_edit, "hide", "密码", _func, position=QLineEdit.ActionPosition.LeadingPosition)
	line_edit.setEchoMode(QLineEdit.EchoMode.Password)
	line_edit.setReadOnly(True)


def open_folder(folder_path: str):
	if os.path.isfile(folder_path):
		folder_path = os.path.dirname(folder_path)
	if not os.path.exists(folder_path):
		return
	QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))


class FileIO:
	@staticmethod
	def read(file_path, encoding = "utf-8"):
		file_type = os.path.splitext(file_path)[1]
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
	def write(file_path, datas, encoding = "utf-8"):
		file_type = os.path.splitext(file_path)[1]
		if file_type == ".pkl":
			with open(file_path, mode="wb") as file:
				pickle.dump(datas, cast(file))
		elif file_type == ".json":
			with open(file_path, mode="w", encoding=encoding) as file:
				json.dump(datas, cast(file))
		else:
			with open(file_path, mode="w", encoding=encoding) as file:
				file.write(datas)


class Tree:
	@staticmethod
	def scan(tree_widget: QTreeWidget, folder_path: str, check=False):
		def _func(path_parent, parent):
			entry = QDir(path_parent).entryList(QDir.Filter.Dirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)
			entry.sort(key=lambda x: tuple(reversed(os.path.splitext(x))))

			for name in entry:
				path_child = join_path(path_parent, name)
				if os.path.isdir(path_child):
					ico = "folder"
				else:
					ico = file_icons.get(os.path.splitext(path_child)[1].lower(), "file")

				child = QTreeWidgetItem([name])
				child.setText(0, name)
				child.setIcon(0, icon(ico))
				child.setToolTip(0, path_child)
				child.setCheckState(0, Qt.CheckState.Unchecked) if check else None
				parent.addChild(child) if parent else tree_widget.addTopLevelItem(child)
				_func(path_child, child) if ico == "folder" else None

		file_icons = {
			".mp4": "video", ".m4s": "video", ".mp3": "audio",
			".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
		}
		tree_widget.clear()
		if os.path.exists(folder_path):
			_func(folder_path, cast(None))

	@staticmethod
	def select(tree_widget: QTreeWidget):
		def _func(item):
			cast(tree_widget).itemChanged.disconnect(_func)

			leaves = [item]
			while leaves:
				leaf = leaves.pop(0)
				leaf.setCheckState(0, item.checkState(0))
				for i in range(leaf.childCount()):
					leaves.append(leaf.child(i))

			root = item.parent()
			while root:
				count = sum(root.child(i).checkState(0) != Qt.CheckState.Unchecked for i in range(root.childCount()))
				if count == root.childCount():
					root.setCheckState(0, Qt.CheckState.Checked)
				elif not count:
					root.setCheckState(0, Qt.CheckState.Unchecked)
				else:
					root.setCheckState(0, Qt.CheckState.PartiallyChecked)
				root = root.parent()

			cast(tree_widget.itemChanged).connect(_func)

		cast(tree_widget.itemChanged).connect(_func)


class Menu:
	@staticmethod
	def menu(widget, select: bool = False, folder: bool = False, func: callable = None):
		def _func(point):
			widget.setProperty("menu", QMenu(widget))
			item = widget.itemAt(point)
			if not item:
				return
			widget.setCurrentItem(item)

			if select:
				Menu.add(widget.property("menu"), "select_all", "全选", lambda: Menu.select_all(widget))
				Menu.add(widget.property("menu"), "unselect_all", "取消全选", lambda: Menu.unselect_all(widget))
			if folder:
				if isinstance(widget, QTreeWidget) and widget.currentItem().toolTip(0):
					Menu.add(widget.property("menu"), "export", "打开文件夹", lambda: open_folder(item.toolTip(0)))
				elif isinstance(widget, QListWidget) and widget.currentItem().toolTip():
					Menu.add(widget.property("menu"), "export", "打开文件夹", lambda: open_folder(item.toolTip()))

			func(widget, point) if func else None
			widget.property("menu").exec(widget.viewport().mapToGlobal(point))

		widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		cast(widget).customContextMenuRequested.connect(_func)

	@staticmethod
	def select_all(widget: QTreeWidget | QListWidget):
		if isinstance(widget, QTreeWidget):
			for i in range(widget.topLevelItemCount()):
				widget.topLevelItem(i).setCheckState(0, Qt.CheckState.Checked)
		elif isinstance(widget, QListWidget):
			for i in range(widget.count()):
				widget.item(i).setCheckState(Qt.CheckState.Checked)

	@staticmethod
	def unselect_all(widget: QTreeWidget | QListWidget):
		if isinstance(widget, QTreeWidget):
			for i in range(widget.topLevelItemCount()):
				widget.topLevelItem(i).setCheckState(0, Qt.CheckState.Unchecked)
		elif isinstance(widget, QListWidget):
			for i in range(widget.count()):
				widget.item(i).setCheckState(Qt.CheckState.Unchecked)

	@staticmethod
	def open_folder(widget: QTreeWidget | QListWidget):
		if isinstance(widget, QTreeWidget):
			open_folder(widget.currentItem().toolTip(0))
		elif isinstance(widget, QListWidget):
			open_folder(widget.currentItem().toolTip())

	@staticmethod
	def add(widget, ico: str, text: str, func: callable):
		action = QAction(text, widget)
		action.setIcon(icon(ico))
		cast(action).triggered.connect(func)
		widget.addAction(action)


class Sync:
	@staticmethod
	def scroll(self, widget_old, widget_new):
		def _func(value):
			widget = self.sender()
			cast(widgets[widget]).valueChanged.disconnect(_func)
			widgets[widget].setValue(value)
			cast(widgets[widget]).valueChanged.connect(_func)

		vbar_old, hbar_old = widget_old.verticalScrollBar(), widget_old.horizontalScrollBar()
		vbar_new, hbar_new = widget_new.verticalScrollBar(), widget_new.horizontalScrollBar()
		widgets = {vbar_old: vbar_new, hbar_old: hbar_new, vbar_new: vbar_old, hbar_new: hbar_old}

		cast(vbar_old).valueChanged.connect(_func)
		cast(vbar_new).valueChanged.connect(_func)
		cast(hbar_old).valueChanged.connect(_func)
		cast(hbar_new).valueChanged.connect(_func)


	@staticmethod
	def select(self, widget_old: QListWidget, widget_new: QListWidget):
		def _func():
			widget = self.sender()
			widgets[widget].setCurrentRow(widget.currentRow())

		widgets = {widget_old: widget_new, widget_new: widget_old}
		cast(widget_old).itemSelectionChanged.connect(_func)
		cast(widget_new).itemSelectionChanged.connect(_func)
