import json
with open("reward_history.json") as f:
    rewards = json.load(f)

window = 1000
smoothed = []
running = 0.0
for i, r in enumerate(rewards):
    running += r
    if i >= window:
        running -= rewards[i - window]
    smoothed.append(running / min(i + 1, window))
    
import csv
with open("smoothed_rewards.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Episode", "Reward", "Smoothed"])
    for i in range(len(rewards)):
        w.writerow([i + 1, f"{rewards[i]:.1f}", f"{smoothed[i]:.1f}"])