from PyQt6.QtCore import pyqtSignal, QDir, QSize, QTimer, Qt, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QImage, QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QFileDialog, QLineEdit, QListWidget, QMenu, QMessageBox
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
import json
import os
import pickle
import re
import sys

RESOURCE = os.path.join(getattr(sys, "_MEIPASS", os.path.abspath("..")), "static").replace("\\", "/")
BANNED_CHAR = re.compile(r'[\\/*?:"<>|]')


def cast(obj):
	return obj


def join_path(*paths):
	return os.path.join("", *paths).replace("\\", "/")


def icon(path):
	return QIcon(join_path(RESOURCE, "common", f"{path}.png"))


def timer(interval, func):
	t = QTimer()
	t.setInterval(interval)
	cast(t).timeout.connect(func)
	return t


def pixmap(label=None, size=None, color=None, image=None):
	if image:
		if isinstance(image, str):
			image = QImage(f"{image}.png")
		pm = QPixmap().fromImage(image)
	else:
		if isinstance(size, QSize):
			size = size.width(), size.height()
		if isinstance(size, int):
			size = (size,) * 2
		pm = QPixmap(*tuple(size)) if size else label.pixmap()
		pm.fill(color) if color else None
	label.setPixmap(pm) if label else None
	return pm


def signal(func):
	s = pyqtSignal()
	cast(s).connect(func)
	return s


def dialog(msg, msg_type):
	message_box = QMessageBox()
	message_box.setText(msg)
	message_box.setWindowIcon(icon(msg_type))
	message_box.setWindowTitle(" ")

	if msg_type == "warning":
		message_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
	return message_box.exec() == QMessageBox.StandardButton.Yes


def button(push_button, func, ico=None, tip=None, ico_size=None):
	cast(push_button).clicked.connect(func)
	push_button.setIcon(icon(ico)) if ico else None
	push_button.setToolTip(tip) if tip else None
	push_button.setIconSize(QSize(ico_size, ico_size)) if ico_size is not None else None
	push_button.setCursor(Qt.CursorShape.PointingHandCursor)


def select_folder(line_edit, push_button, func):
	def _select():
		folder_path = QFileDialog.getExistingDirectory(directory=line_edit.text())
		if not os.path.exists(folder_path):
			return
		line_edit.setText(folder_path)
		func() if func else None

	action = QAction(line_edit)
	action.setIcon(icon("open_folder"))
	action.setToolTip("打开文件夹")
	cast(action).triggered.connect(lambda: open_folder(line_edit.text()))

	button(push_button, _select, "folder") if push_button else None
	line_edit.setReadOnly(True)
	line_edit.setToolTip(line_edit.placeholderText())
	line_edit.addAction(action, QLineEdit.ActionPosition.TrailingPosition)


def open_folder(folder_path):
	if os.path.isfile(folder_path):
		folder_path = os.path.dirname(folder_path)
	if not os.path.exists(folder_path):
		return
	QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))


def screen_info():
	app = QApplication([])
	screen = app.primaryScreen()
	app.quit()
	return {
		"size": (screen.size().width(), screen.size().height()),
		"dpr": screen.devicePixelRatio()
	}


def read(file_path):
	extension = os.path.splitext(file_path)[1]
	if extension == ".pkl":
		with open(file_path, mode="rb") as file:
			datas = pickle.load(file)
	elif extension == ".json":
		with open(file_path, mode="r", encoding="utf-8") as file:
			datas = json.load(file)
	else:
		with open(file_path, mode="r", encoding="utf-8") as file:
			datas = file.read()
	print(f"[READ] {file_path}")
	return datas


def write(file_path, datas):
	extension = os.path.splitext(file_path)[1]
	if extension == ".pkl":
		with open(file_path, mode="wb") as file:
			pickle.dump(datas, cast(file))
	elif extension == ".json":
		with open(file_path, mode="w", encoding="utf-8") as file:
			json.dump(datas, cast(file))
	else:
		with open(file_path, mode="w", encoding="utf-8") as file:
			file.write(datas)
	print(f"[WRITE] {file_path}")


class Tree:
	@staticmethod
	def scan(tree_widget, folder_path, check=False):
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
	def select(tree_widget):
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
	def menu(widget, select=False, folder=False, func=None):
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
	def select_all(widget):
		if isinstance(widget, QTreeWidget):
			for i in range(widget.topLevelItemCount()):
				widget.topLevelItem(i).setCheckState(0, Qt.CheckState.Checked)
		elif isinstance(widget, QListWidget):
			for i in range(widget.count()):
				widget.item(i).setCheckState(Qt.CheckState.Checked)

	@staticmethod
	def unselect_all(widget):
		if isinstance(widget, QTreeWidget):
			for i in range(widget.topLevelItemCount()):
				widget.topLevelItem(i).setCheckState(0, Qt.CheckState.Unchecked)
		elif isinstance(widget, QListWidget):
			for i in range(widget.count()):
				widget.item(i).setCheckState(Qt.CheckState.Unchecked)

	@staticmethod
	def open_folder(widget):
		if isinstance(widget, QTreeWidget):
			open_folder(widget.currentItem().toolTip(0))
		elif isinstance(widget, QListWidget):
			open_folder(widget.currentItem().toolTip())

	@staticmethod
	def add(widget, ico, text, func):
		action = QAction(text, widget)
		action.setIcon(icon(ico))
		cast(action).triggered.connect(func)
		widget.addAction(action)
