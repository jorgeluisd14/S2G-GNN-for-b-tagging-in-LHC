import torch
import torch.nn as nn

from models.deep_sets import DeepSet
from models.layers import PsiSuffix
from models.set_to_graph import SetToGraph
from models.message_pass import MPNN

class JetClassifier(nn.Module):
    def __init__(self, in_features, vertexing_config, vertexing_type='s2g', cfg=None):
        super().__init__()

        if cfg is None:
            cfg = {}
        self.agg = cfg.get('agg', torch.sum)

        # Only using SetToGraph for vertexing
        self.vertexing = SetToGraph(**vertexing_config)

        self.set_model = DeepSet(in_features=in_features, feats=[126, 126, 126, 126], attention=True, cfg=cfg)
        self.mpnn = MPNN(n_layers=3, edge_network_layers=[126*3+1, 100, 20], node_network_layers=[126+20, 100, 126])

        self.classifier_net = nn.Sequential(
            nn.Linear(126 + 4, 100, bias=False),
            nn.BatchNorm1d(100),
            nn.ReLU(),
            nn.Linear(100, 50, bias=False),
            nn.BatchNorm1d(50),
            nn.ReLU(),
            nn.Linear(50, 3)
        )

    def forward(self, jet_features, x, external_edge_vals=None):
        u = self.set_model(x.transpose(2, 1)).transpose(1, 2)
        n = u.shape[1]

        edge_vals = self.vertexing(x).permute(0, 2, 3, 1) if self.vertexing is not None else external_edge_vals.unsqueeze(3)
        updated_node_rep = self.mpnn(u, edge_vals)

        graph_rep = torch.sum(updated_node_rep, dim=1)
        graph_rep = torch.cat([jet_features, graph_rep], dim=1)

        pred = self.classifier_net(graph_rep)
        return pred
