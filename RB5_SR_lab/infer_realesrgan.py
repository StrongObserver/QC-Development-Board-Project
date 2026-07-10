"""
A1 — Minimal standalone Real-ESRGAN (realesr-general-x4v3) inference.

Why standalone: the official inference_realesrgan.py pulls in basicsr/realesrgan,
which import torchvision.transforms.functional_tensor — removed in the torchvision
that ships with torch 2.9. So we define the tiny SRVGGNetCompact arch ourselves and
load the .pth directly. Runs on CPU (this PC's CUDA driver is currently inactive).

Usage:
  python3 infer_realesrgan.py --input inputs/foo.png --outdir results
"""
import argparse
import os
import time

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class SRVGGNetCompact(nn.Module):
    """Compact VGG-style super-resolution net (matches realesr-general-x4v3).

    Architecture is stored in the checkpoint as a flat `body` ModuleList:
      body.0  : Conv(3 -> 64)
      body.1  : PReLU(64)
      body.2..: (Conv(64->64), PReLU(64)) x num_conv
      body.last: Conv(64 -> 3 * upscale^2)
    followed by PixelShuffle(upscale). The network learns the residual on top of a
    nearest-neighbour upsample of the input.
    """

    def __init__(self, num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=32,
                 upscale=4, act_type='prelu'):
        super().__init__()
        self.upscale = upscale
        self.body = nn.ModuleList()
        # first conv + activation
        self.body.append(nn.Conv2d(num_in_ch, num_feat, 3, 1, 1))
        self.body.append(self._act(act_type, num_feat))
        # body: num_conv x (conv + activation)
        for _ in range(num_conv):
            self.body.append(nn.Conv2d(num_feat, num_feat, 3, 1, 1))
            self.body.append(self._act(act_type, num_feat))
        # last conv expands channels for pixel shuffle
        self.body.append(nn.Conv2d(num_feat, num_out_ch * upscale * upscale, 3, 1, 1))
        self.upsampler = nn.PixelShuffle(upscale)

    @staticmethod
    def _act(act_type, num_feat):
        if act_type == 'relu':
            return nn.ReLU(inplace=True)
        if act_type == 'prelu':
            return nn.PReLU(num_parameters=num_feat)
        if act_type == 'leakyrelu':
            return nn.LeakyReLU(negative_slope=0.1, inplace=True)
        raise ValueError(f'unknown act_type {act_type}')

    def forward(self, x):
        out = x
        for layer in self.body:
            out = layer(out)
        out = self.upsampler(out)
        # residual learning: add nearest-neighbour upsample of the input
        base = F.interpolate(x, scale_factor=self.upscale, mode='nearest')
        return out + base


def load_model(weights_path, device):
    model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64,
                            num_conv=32, upscale=4, act_type='prelu')
    ckpt = torch.load(weights_path, map_location='cpu')
    state = ckpt['params'] if 'params' in ckpt else ckpt
    model.load_state_dict(state, strict=True)
    model.eval()
    model.to(device)
    return model


@torch.no_grad()
def enhance(model, img_bgr, device):
    # cv2 gives BGR uint8; model expects RGB float [0,1], NCHW
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    tensor = torch.from_numpy(img_rgb).permute(2, 0, 1).unsqueeze(0).to(device)
    out = model(tensor)
    out = out.clamp(0, 1).squeeze(0).permute(1, 2, 0).cpu().numpy()
    out_bgr = cv2.cvtColor((out * 255.0).round().astype(np.uint8), cv2.COLOR_RGB2BGR)
    return out_bgr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help='input image path')
    ap.add_argument('--weights', default='weights/realesr-general-x4v3.pth')
    ap.add_argument('--outdir', default='results')
    args = ap.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'[info] device = {device}')

    model = load_model(args.weights, device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f'[info] model loaded, {n_params/1e6:.2f}M params')

    img = cv2.imread(args.input, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(args.input)
    h, w = img.shape[:2]
    print(f'[info] input {w}x{h}')

    t0 = time.time()
    out = enhance(model, img, device)
    dt = time.time() - t0
    oh, ow = out.shape[:2]
    print(f'[info] output {ow}x{oh}  ({dt*1000:.0f} ms on {device})')

    os.makedirs(args.outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.input))[0]
    out_path = os.path.join(args.outdir, f'{base}_x4.png')
    cv2.imwrite(out_path, out)
    # also save a bicubic x4 of the input for an honest side-by-side baseline
    bicubic = cv2.resize(img, (ow, oh), interpolation=cv2.INTER_CUBIC)
    bicubic_path = os.path.join(args.outdir, f'{base}_bicubic_x4.png')
    cv2.imwrite(bicubic_path, bicubic)
    print(f'[ok] wrote {out_path}')
    print(f'[ok] wrote {bicubic_path}  (bicubic baseline for comparison)')


if __name__ == '__main__':
    main()
