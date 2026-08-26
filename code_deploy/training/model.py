"""
model.py

ResNet18 + XGBoost hybrid -- your original architecture, kept as-is.

Pipeline:
  1. GeoResNet (ResNet18 backbone, first conv adapted for 6 input channels)
     is fine-tuned end-to-end on the binary label as a pretext task.
  2. Its penultimate-layer output (512-dim) is then used as a fixed
     embedding extractor.
  3. Those embeddings are concatenated with hand-crafted tabular features
     (per-band mean/std) and fed into XGBoost for the final prediction.
"""

import torch
import torch.nn as nn
import torchvision.models as models


class GeoResNet(nn.Module):
    def __init__(self, in_channels=6, num_classes=2):
        super().__init__()
        try:
            self.resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        except Exception as e:
            print(f"WARNING: could not download pretrained ImageNet weights ({e}). "
                  f"Falling back to random init -- expect worse/slower convergence.")
            self.resnet = models.resnet18(weights=None)

        old_conv = self.resnet.conv1
        new_conv = nn.Conv2d(
            in_channels, old_conv.out_channels,
            kernel_size=old_conv.kernel_size, stride=old_conv.stride,
            padding=old_conv.padding, bias=False,
        )
        with torch.no_grad():
            avg_weight = old_conv.weight.mean(dim=1, keepdim=True)
            new_conv.weight.copy_(avg_weight.repeat(1, in_channels, 1, 1))
        self.resnet.conv1 = new_conv

        self.embedding_dim = self.resnet.fc.in_features  # 512 for resnet18
        self.resnet.fc = nn.Linear(self.embedding_dim, num_classes)
        self._embedding_mode = False

    def forward(self, x):
        if self._embedding_mode:
            x = self.resnet.conv1(x)
            x = self.resnet.bn1(x)
            x = self.resnet.relu(x)
            x = self.resnet.maxpool(x)
            x = self.resnet.layer1(x)
            x = self.resnet.layer2(x)
            x = self.resnet.layer3(x)
            x = self.resnet.layer4(x)
            x = self.resnet.avgpool(x)
            x = torch.flatten(x, 1)
            return x
        return self.resnet(x)

    def set_embedding_mode(self, flag: bool):
        self._embedding_mode = flag
