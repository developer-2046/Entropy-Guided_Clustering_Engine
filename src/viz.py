import matplotlib.pyplot as plt

def plot_clusters(X, labels, centers=None, title="Clusters"):
    plt.scatter(X[:, 0], X[:, 1], c=labels, cmap='viridis', s=30)
    if centers is not None:
        plt.scatter(centers[:, 0], centers[:, 1], c='red', s=100, marker='X')
    plt.title(title)
    plt.grid(True)
    plt.show()
