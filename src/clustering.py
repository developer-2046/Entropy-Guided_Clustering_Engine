import numpy as np

def build_lstm_data(df, feature_cols, label_col="Cluster", window_size=20):
    X = []
    y = []
    data = df[feature_cols + [label_col]].dropna().values

    for i in range(window_size, len(data)):
        X.append(data[i-window_size:i, :-1])  # last 20 rows, all features
        y.append(data[i, -1])                 # label on day 21

    return np.array(X), np.array(y)
