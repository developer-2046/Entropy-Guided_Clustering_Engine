import numpy as np

def calculate_entropy(prob_vector):
    """Calculate Shannon entropy from a probability distribution."""
    prob_vector = np.array(prob_vector)
    prob_vector = prob_vector[prob_vector > 0]  # Avoid log(0)
    return -np.sum(prob_vector * np.log2(prob_vector))
