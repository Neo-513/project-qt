from src.game2048 import *

def compute_sequential():
	__compute_moves(PATH["sequential"], slice(None, None, None))


def compute_reversed():
	__compute_moves(PATH["reversed"], slice(None, None, -1))


def __compute_moves(path, piece):
	cache = {}
	for tiles in product(range(12), repeat=4):
		t, merged = [], False
		for tile in tiles:
			if tile == 0:
				continue
			if t and t[-1] == tile and not merged:
				t[-1] += 1
				merged = True
			else:
				t.append(tile)
				merged = False
		cache[tiles[piece].tobytes()] = np.array(t + [0] * (4 - len(t)), dtype=np.int8)[piece]
	util.write(path, cache)


def compute_mono():
	cache = {}
	for tiles in product(range(12), repeat=4):
		t = np.diff(tiles)
		cache[bytes(tiles)] = np.sum(tiles) if np.all(t >= 0) or np.all(t <= 0) else 0
	util.write(PATH["mono"], cache)


def compute_smooth():
	cache = {}
	for tiles in product(range(12), repeat=4):
		cache[bytes(tiles)] = np.sum(np.abs(np.diff(tiles)))
	util.write(PATH["smooth"], cache)


def compute_merge():
	cache = {}
	for tiles in product(range(12), repeat=4):
		t = np.array(tiles)
		t = t[t != 0]
		cache[bytes(tiles)] = np.sum(t[:-1][np.diff(t) == 0])
	util.write(PATH["merge"], cache)


def compute_background():
	application = QApplication([])
	pixmap = util.pixmap(size=475, color=QColor(187, 173, 160))
	with QPainter(pixmap) as painter:
		for groove in MyDisplayer.GROOVE.values():
			MyDisplayer.draw(painter, 0, groove)
	pixmap.save("background.png")
	application.quit()


if __name__ == "__main__":
	# compute_sequential()
	# compute_reversed()
	# compute_mono()
	# compute_smooth()
	# compute_merge()
	# compute_background()
	pass
