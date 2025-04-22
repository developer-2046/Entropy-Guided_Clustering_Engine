import torch
import torch.nn as nn

class RegimeLSTM(nn.Module):
    def __init__(self, input_dim=7, hidden_dim=64, num_layers=2, num_classes=4):
        super(RegimeLSTM, self).__init__()
        self.LSTM = nn.LSTM(input_size=input_dim, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True)
        self.dropout = nn.Dropout(0.3)
        self.fc = nn.Linear(hidden_dim, num_classes)

    def forward(self, X):
        out, _ = self.LSTM(X)
        out = out[:, 1, :]
        out = self.dropout(out)
        return self.fc(out)

