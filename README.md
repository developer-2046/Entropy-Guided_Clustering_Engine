# 🧠 Entropy-Guided Clustering Engine

> Regime detection and deep learning-based interpretability on SP500 closing prices using entropy, network structure, and transformers.
> Check it out: https://entropy-engine.netlify.app/

---

## 📂 Project Structure

```
Entropy-Guided Clustering Engine/
│
├── data/                         # Raw and processed market data
│   ├── data.csv                  # Feature-enriched SP500 data (entropy, eigenvalues)
│   └── sp_with_gics.csv          # Raw SP500 closing prices with GICS sectors
│
├── notebooks/                    # Interactive development & demos
│   ├── 01_intro_clustering.ipynb # Full System Pipeline
├── src/                          # Source code
│   ├── clustering.py             # Feature engineering, entropy, correlation
│   ├── entropy_utils.py          # Shannon entropy & eigenvalue processing
│   ├── lstm_dataset.py           # PyTorch Dataset builder (sliding window)
│   ├── lstm_model.py             # LSTM-based classifier
│   ├── transformer_model.py      # Transformer with self-attention logic
│   └── viz.py                    # Visualization utilities
│
├── requirements.txt              # Dependency list
└── README.md                     # You're here
```

---

## 💡 Project Highlights

- Calculates **Shannon Entropy** from eigenvectors of correlation-distance matrices
- Extracts **λ₁, λ₂, λ₃**, **average degree**, and **network entropy**
- Clusters feature windows into regimes using **K-Means**
- Projects regime space using **PCA**
- Overlays major market **crashes** on time series
- Trains:
  - A **LSTM** to predict regime transitions
  - A **Transformer** to learn temporal dependencies with **self-attention**
- Visualizes attention maps to show which time steps influenced the model

---

## 📊 Key Features Extracted

| Feature             | Description                                      |
|---------------------|--------------------------------------------------|
| Shannon Entropy     | System uncertainty from normalized eigenvectors |
| Network Entropy     | Topological complexity of MST graph             |
| Average Degree      | Graph connectivity level                        |
| λ₁, λ₂, λ₃           | Largest eigenvalues of distance matrix          |
| Mean Correlation    | Global correlation between stocks               |

---

## 🔹 Models Trained

| Model         | Input (20-day window) | Target          | Accuracy |
|---------------|------------------------|------------------|----------|
| LSTM          | 7 entropy features     | Regime cluster   | ~36%     |
| Transformer   | 7 entropy features     | Regime cluster   | ~26%     |

---

## 🔹 Attention Visualization

Each heatmap shows how much each day in the 20-day sequence attends to others. Helps identify high-influence days that drive regime predictions.

---

## ▶️ Run Locally

```bash
git clone https://github.com/your-username/entropy-guided-clustering-engine.git
cd entropy-guided-clustering-engine
pip install -r requirements.txt
```

Then launch Jupyter and run the notebooks in this order:
1. `01_intro_clustering.ipynb`

---

## 🔖 TODO

- [ ] Sector-wise correlation breakdown
- [ ] GAT-style temporal attention
- [ ] Regime-based portfolio simulation
- [ ] Convert into a Streamlit dashboard

---

## 📃 Author

Built by **[Yuvraj Malik](https://github.com/developer-2046)**  
CS + Applied Math @ University of Utah  
Exploring AI × Financial Modeling × Research Engineering
