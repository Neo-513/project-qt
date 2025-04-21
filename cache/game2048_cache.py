from itertools import product
import numpy as np
import pickle


def compute_sequential():
	__compute_moves("cache_sequential.pkl", 1)


def compute_reversed():
	__compute_moves("cache_reversed.pkl", -1)


def __compute_moves(file_path, step):
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
		cache[bytes(tiles[::step])] = np.array(t + [0] * (4 - len(t)), dtype=np.uint8)[::step]
	with open(file_path, mode="wb") as file:
		pickle.dump(cache, file)


def compute_mono():
	cache = {}
	for tiles in product(range(12), repeat=4):
		t = np.diff(tiles)
		cache[bytes(tiles)] = np.sum(tiles) if np.all(t >= 0) or np.all(t <= 0) else 0
	with open("cache_mono.pkl", mode="wb") as file:
		pickle.dump(cache, file)


def compute_smooth():
	cache = {}
	for tiles in product(range(12), repeat=4):
		cache[bytes(tiles)] = np.sum(np.abs(np.diff(tiles)))
	with open("cache_smooth.pkl", mode="wb") as file:
		pickle.dump(cache, file)


def compute_merge():
	cache = {}
	for tiles in product(range(12), repeat=4):
		t = np.array([tile for tile in tiles if tile != 0])
		cache[bytes(tiles)] = np.sum(t[:-1][np.diff(t) == 0])
	with open("cache_merge.pkl", mode="wb") as file:
		pickle.dump(cache, file)


def compute_trail():
	trails = {"L": {}, "R": {}, "U": {}, "D": {}}
	trans = {
		"L": lambda x, y: (x, y),
		"R": lambda x, y: (3 - x, 3 - y),
		"U": lambda x, y: (y, 3 - x),
		"D": lambda x, y: (3 - y, x)
	}
	for (movement, trail), (i, j, k) in product(trails.items(), product(range(4), repeat=3)):
		if k <= j:
			balanced = (i, j), (i, k)
			raw = trans[movement](*balanced[0]), trans[movement](*balanced[1])
			trail[raw] = balanced

	cache = {"L": {}, "R": {}, "U": {}, "D": {}}
	for movement, trail in trails.items():
		c = cache[movement]
		for raw, balanced in trail.items():
			sx, sy = raw[0][1] * 115 + 15, raw[0][0] * 115 + 15
			ex, ey = raw[1][1] * 115 + 15, raw[1][0] * 115 + 15
			dx, dy = ex - sx, ey - sy
			c[balanced] = [(round(sx + dx * offset), round(sy + dy * offset)) for offset in np.arange(0.1, 1.1, 0.1)]
	with open("cache_trail.pkl", mode="wb") as file:
		pickle.dump(cache, file)


if __name__ == "__main__":
	# compute_sequential()
	# compute_reversed()
	# compute_mono()
	# compute_smooth()
	# compute_merge()
	# compute_trail()
	pass
