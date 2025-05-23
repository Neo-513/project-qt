from src.wordle import *
from collections import Counter
from multiprocessing import cpu_count, Pool


def compute_index():
	cache = {word: i for i, word in enumerate(ALLOWED_WORDS)}
	util.write(PATH["index"], cache)


def compute_compose():
	cache = {word: dict(Counter(word)) for word in ALLOWED_WORDS}
	util.write(PATH["compose"], cache)


def compute_state():
	cache = np.zeros(MyComputation.TOTALITY ** 2, dtype=np.uint8)
	for (i, guess), (j, answer) in product(enumerate(ALLOWED_WORDS), repeat=2):
		cache[i * MyComputation.TOTALITY + j] = __compute_state(guess, answer)
	cache.tofile(PATH["state"])


def __compute_state(guess, answer):
	state, compose, uncertain = ["0"] * 5, CACHE["compose"][answer].copy(), []
	for i, g in enumerate(guess):
		if g == answer[i]:
			state[i] = "2"
			compose[g] -= 1
		elif g in answer:
			uncertain.append(i)
	for i in uncertain:
		if compose[guess[i]]:
			state[i] = "1"
			compose[guess[i]] -= 1
	return int("".join(state), 3)


def compute_worst(worst):
	tasks = ((guess, int(worst, 3)) for guess in ALLOWED_WORDS)
	with Pool(processes=cpu_count()) as pool:
		cache = dict(pool.imap_unordered(__compute_worst, tasks))
		util.write(PATH[f"worst_{worst}"], cache)


def __compute_worst(args):
	guess, state = args
	candidate = MyComputation.to_candidate(guess, state, ALLOWED_WORDS)
	best_guess = EntropyAlgorithm.solve(candidate)
	print(guess, len(candidate))
	return guess, best_guess


if __name__ == "__main__":
	# compute_index()
	# compute_compose()
	# compute_state()
	# compute_worst("00000")
	# compute_worst("00001")
	# compute_worst("00010")
	# compute_worst("00100")
	# compute_worst("01000")
	# compute_worst("10000")
	pass
