"""Prepare offline SR eval assets from public web image sources.

The Android app uses these 128x128 PNG assets so we can test text/edge and
low-light/noise scenarios without staging a physical scene in front of the RB5.
"""

from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "RB5VisionLab" / "app" / "src" / "main" / "assets"
RAW_DIR = Path(__file__).resolve().parent / "inputs" / "offline_eval_sources"

SOURCES = {
    "offline_text_edge_128.png": {
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Snellen06.png",
        "raw": "snellen06.png",
        "kind": "text_edge",
        "source_note": "Wikimedia Commons File:Snellen06.png; public-domain Snellen eye chart.",
    },
    "offline_lowlight_noise_128.png": {
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Airport_night_ISO_1600.jpg",
        "raw": "airport_night_iso_1600.jpg",
        "kind": "lowlight_noise",
        "source_note": "Wikimedia Commons Category:Image noise sample Airport night ISO 1600.jpg.",
    },
}


def download(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "RB5VisionLab eval asset preparation"})
    with urlopen(req, timeout=60) as response:
        output.write_bytes(response.read())


def center_crop_square(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    side = min(h, w)
    top = (h - side) // 2
    left = (w - side) // 2
    return image[top:top + side, left:left + side]


def prepare_text_edge(image: np.ndarray) -> np.ndarray:
    # Keep the chart structure and high-contrast text strokes.
    square = center_crop_square(image)
    return cv2.resize(square, (128, 128), interpolation=cv2.INTER_AREA)


def prepare_lowlight_noise(image: np.ndarray) -> np.ndarray:
    # Use the darker center crop and slightly downscale to a stable 128x128 input.
    square = center_crop_square(image)
    crop = cv2.resize(square, (128, 128), interpolation=cv2.INTER_AREA)
    # Preserve a low-light/noisy character even if the downloaded sample is bright.
    dark = np.clip(crop.astype(np.float32) * 0.55, 0, 255).astype(np.uint8)
    rng = np.random.default_rng(20260713)
    noise = rng.normal(0, 7.0, dark.shape).astype(np.float32)
    return np.clip(dark.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for asset_name, info in SOURCES.items():
        raw_path = RAW_DIR / info["raw"]
        if not raw_path.exists():
            print(f"[download] {info['url']}")
            download(info["url"], raw_path)
        image = cv2.imread(str(raw_path), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"cannot read {raw_path}")
        if info["kind"] == "text_edge":
            prepared = prepare_text_edge(image)
        else:
            prepared = prepare_lowlight_noise(image)
        output_path = ASSETS / asset_name
        cv2.imwrite(str(output_path), prepared)
        print(f"[ok] wrote {output_path} from {info['source_note']}")


if __name__ == "__main__":
    main()
