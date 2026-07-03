"""M5 — train the U-Net transition surrogate. Usage: uv run python scripts/05_train.py [n_rollouts] [epochs]"""
import sys
from mal_ghana_sim import config as C, train

n = int(sys.argv[1]) if len(sys.argv) > 1 else C.N_ROLLOUTS
ep = int(sys.argv[2]) if len(sys.argv) > 2 else C.TRAIN_EPOCHS
model, best_dice = train.train(n_rollouts=n, epochs=ep)
