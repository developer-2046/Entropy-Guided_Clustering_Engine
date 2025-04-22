import torch
import torch.nn as nn

class TransformerBlock(nn.Module):
    def __init__(self, dim, heads=4, ff_hidden=128, dropout=0.1):
        super().__init__()
        self.attn = nn.MultiheadAttention(embed_dim=dim, num_heads=heads, batch_first=True)
        self.norm1 = nn.LayerNorm(dim)
        self.ff = nn.Sequential(
            nn.Linear(dim, ff_hidden),
            nn.ReLU(),
            nn.Linear(ff_hidden, dim),
        )
        self.norm2 = nn.LayerNorm(dim)
        self.drop = nn.Dropout(dropout)

    def forward(self, x, return_attention=False):
        if return_attention:
            attn_out, attn_weights = self.attn(x, x, x, need_weights=True)
        else:
            attn_out = self.attn(x, x, x)[0]  # just the output, ignore attention weights

        x = self.norm1(x + self.drop(attn_out))
        ff_out = self.ff(x)
        out = self.norm2(x + self.drop(ff_out))

        if return_attention:
            return out, attn_weights
        return out


class TransformerClassifier(nn.Module):
    def __init__(self, seq_len=20, input_dim=7, emb_dim=64, num_heads=4, num_classes=4):
        super().__init__()
        self.embedding = nn.Linear(input_dim, emb_dim)
        self.transformer = TransformerBlock(emb_dim, heads=num_heads)
        self.pool = nn.AdaptiveAvgPool1d(1)  # reduce [B, T, D] → [B, D]
        self.fc = nn.Linear(emb_dim, num_classes)

    def forward(self, x, return_attention=False):
        x = self.embedding(x)

        if return_attention:
            x, attn_weights = self.transformer(x, return_attention=True)
        else:
            x = self.transformer(x)

        x = x.transpose(1, 2)
        x = self.pool(x).squeeze(-1)
        logits = self.fc(x)

        return (logits, attn_weights) if return_attention else logits




