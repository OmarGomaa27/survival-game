import json
import matplotlib.pyplot as plt

with open("reward_history.json") as f:
    rewards = json.load(f)
window = 50
smoothed = [sum(rewards[max(0,i-window):i+1]) / 
            min(i+1, window) for i in range(len(rewards))]

plt.figure(figsize=(10, 5))
plt.plot(rewards,   alpha=0.3, color='cyan',  label='Raw reward')
plt.plot(smoothed,  color='orange',           label='50-ep rolling avg')
plt.axhline(y=0,    color='red', linestyle='--', alpha=0.5)
plt.xlabel("Episode")
plt.ylabel("Total Reward")
plt.title("Q-Learning Agent Reward per Episode: ")
plt.legend()
plt.tight_layout()
plt.savefig("convergence_plot.png", dpi=150)
plt.show()