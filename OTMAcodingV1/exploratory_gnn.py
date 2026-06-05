"""Exploratory small-n GNN baseline for supplementary reporting only."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from .baseline_suite import executable_pressure
from .validation_protocols import make_folds, physical_board_id


def _graph_data(record):
    import torch
    from torch_geometric.data import Data

    pos, feat, weights = record.ot_repr
    pos = np.asarray(pos, dtype=float)
    feat = np.asarray(feat, dtype=float)
    weights = np.asarray(weights, dtype=float)
    x = np.column_stack([pos, feat, weights])
    distances = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=2)
    edges = []
    for index in range(len(pos)):
        neighbors = np.argsort(distances[index])[1 : min(5, len(pos))]
        edges.extend((index, int(neighbor)) for neighbor in neighbors)
        edges.extend((int(neighbor), index) for neighbor in neighbors)
    edge_index = np.asarray(edges, dtype=np.int64).T if edges else np.empty((2, 0), dtype=np.int64)
    return Data(
        x=torch.as_tensor(x, dtype=torch.float32),
        edge_index=torch.as_tensor(edge_index, dtype=torch.long),
        y=torch.tensor([record.press_raw], dtype=torch.float32),
    )


def _fit_predict(train_cases: Sequence, test_cases: Sequence, seed: int, epochs: int = 60) -> list[float]:
    import torch
    from torch.nn import Linear, ReLU, Sequential
    from torch_geometric.loader import DataLoader
    from torch_geometric.nn import GCNConv, global_mean_pool

    torch.manual_seed(seed)
    np.random.seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    graphs = [_graph_data(case) for case in train_cases]
    validation_count = max(1, len(graphs) // 5)
    train_graphs = graphs[:-validation_count] if len(graphs) > validation_count else graphs
    valid_graphs = graphs[-validation_count:]

    class SmallGCN(torch.nn.Module):
        def __init__(self, n_features: int):
            super().__init__()
            self.conv1 = GCNConv(n_features, 32)
            self.conv2 = GCNConv(32, 32)
            self.head = Sequential(Linear(32, 16), ReLU(), Linear(16, 1))

        def forward(self, data):
            x = torch.relu(self.conv1(data.x, data.edge_index))
            x = torch.relu(self.conv2(x, data.edge_index))
            x = global_mean_pool(x, data.batch)
            return self.head(x).squeeze(-1)

    model = SmallGCN(graphs[0].num_node_features).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4)
    loss_fn = torch.nn.L1Loss()
    train_loader = DataLoader(train_graphs, batch_size=min(8, len(train_graphs)), shuffle=True)
    valid_loader = DataLoader(valid_graphs, batch_size=min(8, len(valid_graphs)), shuffle=False)
    best_state, best_loss, patience = None, np.inf, 0
    for _ in range(epochs):
        model.train()
        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            loss = loss_fn(model(batch), batch.y)
            loss.backward()
            optimizer.step()
        model.eval()
        with torch.no_grad():
            losses = [float(loss_fn(model(batch.to(device)), batch.to(device).y).item()) for batch in valid_loader]
        valid_loss = float(np.mean(losses)) if losses else np.inf
        if valid_loss < best_loss - 1e-5:
            best_loss = valid_loss
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            patience = 0
        else:
            patience += 1
        if patience >= 12:
            break
    if best_state:
        model.load_state_dict(best_state)
    model.eval()
    predictions = []
    with torch.no_grad():
        for graph in [_graph_data(case) for case in test_cases]:
            graph.batch = torch.zeros(graph.num_nodes, dtype=torch.long)
            predictions.append(executable_pressure(float(model(graph.to(device)).cpu().item())))
    return predictions


def evaluate_exploratory_gnn(records: Sequence, output_dir: str | Path, smoke: bool = False) -> pd.DataFrame:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    seeds = [2026, 2027] if smoke else [2026, 2027, 2028, 2029, 2030]
    folds = make_folds(records, "pcb_group_lobo", max_folds=3 if smoke else None)
    rows = []
    try:
        import torch_geometric  # noqa: F401
    except ImportError as exc:
        frame = pd.DataFrame([{"status": "skipped_dependency", "detail": str(exc)}])
        frame.to_csv(output_dir / "exploratory_gnn_results.csv", index=False)
        return frame
    for fold_index, fold in enumerate(folds, start=1):
        print(f"[exploratory-gnn] outer {fold_index}/{len(folds)} group={fold.fold_id}", flush=True)
        for seed in seeds:
            predictions = _fit_predict(fold.train_cases, fold.test_cases, seed=seed, epochs=30 if smoke else 60)
            for held, prediction in zip(fold.test_cases, predictions):
                error = abs(prediction - held.press_raw)
                rows.append(
                    {
                        "status": "exploratory_small_n_baseline",
                        "seed": seed,
                        "physical_board_id": physical_board_id(held.board_id),
                        "board_id": held.board_id,
                        "observed_pressure_raw": held.press_raw,
                        "recommended_pressure_raw": prediction,
                        "pressure_abs_error_raw": error,
                        "within_0_4_raw": float(error <= 0.4 + 1e-9),
                    }
                )
    frame = pd.DataFrame(rows)
    frame.to_csv(output_dir / "exploratory_gnn_results.csv", index=False)
    summary = (
        frame.groupby("seed", as_index=False)
        .agg(pressure_mae_raw=("pressure_abs_error_raw", "mean"), within_0_4_raw_rate=("within_0_4_raw", "mean"))
    )
    summary.to_csv(output_dir / "exploratory_gnn_seed_summary.csv", index=False)
    return frame

