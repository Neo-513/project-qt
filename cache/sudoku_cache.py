from src.sudoku import *


def compute_graph():
	cache = np.zeros((729, 324), dtype=np.uint8)
	for i, j, k in product(range(9), repeat=3):
		g = cache[i * 81 + j * 9 + k]
		g[i * 9 + j] = g[81 + i * 9 + k] = g[162 + j * 9 + k] = g[243 + i // 3 * 27 + j // 3 * 9 + k] = 1
	cache.tofile(PATH["graph"])


if __name__ == "__main__":
	# compute_graph()
	pass
