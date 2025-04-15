from src.sudoku import *


def compute_graph():
	cache = np.zeros((729, 324), dtype=np.uint8)
	for i, j, k in product(range(9), repeat=3):
		g = cache[i * 81 + j * 9 + k]
		g[i * 9 + j] = g[81 + i * 9 + k] = g[162 + j * 9 + k] = g[243 + i // 3 * 27 + j // 3 * 9 + k] = 1
	cache.tofile(PATH["graph"])


def compute_background():
	application = QApplication([])
	pixmap = util.pixmap(size=540, color=QColor(243, 243, 243))
	with QPainter(pixmap) as painter:
		painter.setPen(QPen(Qt.GlobalColor.gray, 1))
		for pos in product(range(9), repeat=2):
			painter.drawRect(QRect(*np.array((*pos[::-1], 1, 1)) * MyCore.SIZE["block"]))
		painter.setPen(QPen(Qt.GlobalColor.black, 2))
		for pos in product(range(3), repeat=2):
			painter.drawRect(QRect(*np.array((*pos[::-1], 1, 1)) * MyCore.SIZE["block"] * 3))
		painter.drawRect(1, 1, pixmap.width() - 2, pixmap.height() - 2)
	pixmap.save("background.png")
	application.quit()


if __name__ == "__main__":
	# compute_graph()
	# compute_background()
	pass
