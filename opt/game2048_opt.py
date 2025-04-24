from src.game2048 import *
from multiprocessing import cpu_count, Pool
import bayes_opt
import time


def black_box(**weight):
	board = np.zeros((4, 4), dtype=np.uint8)
	MyMatrixer.add(board)
	MyMatrixer.add(board)

	weight = tuple(weight.values())
	threshold = 1200

	for step in range(threshold):
		if MyMatrixer.win(board):
			return (threshold - step) * 10 + 10000
		if MyMatrixer.lose(board) or step >= threshold:
			return step * 5 + np.max(board) * 300
		previous = board.copy()
		board = MyMatrixer.move(board, ExpectimaxAlgorithm.solve(board, weight))
		if 0 in board and not np.array_equal(board, previous):
			MyMatrixer.add(board)
	return 0


def optimize():
	optimizer = bayes_opt.BayesianOptimization(f=black_box, pbounds={f"w{i}": (0, 1) for i in range(5)}, random_state=0)
	optimizer.maximize(init_points=10, n_iter=50)
	print(tuple(round(w, 6) for w in optimizer.max["params"].values()))


def verify():
	weight = {f"w{i}": w for i, w in enumerate(WEIGHT)}
	n = 100
	with Pool(processes=cpu_count()) as pool:
		tictoc = time.time()
		win = sum(score >= 10000 for score in pool.imap_unordered(__verify, (weight for _ in range(n))))
		print(f"[time] {round(time.time() - tictoc, 2)}s  [win] {round(100 * win / n, 2)}%")


def __verify(weight):
	return black_box(**weight)


if __name__ == "__main__":
	# optimize()
	# verify()
	pass
