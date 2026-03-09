"""Interactive region annotator for Mewgent.

Usage:
    python -m uv run python tools/annotate_regions.py <screenshot_path>

Controls:
    Left-click       Place corner point (2 clicks = one rectangle)
    Right-click      Cancel current first point
    N / arrow-up     Cycle to next preset name
    P / arrow-down   Cycle to previous preset name
    U                Undo last region
    Z                Toggle 2x zoom lens at cursor
    S                Save regions.yaml + annotated image and quit
    Q / Esc          Quit without saving
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

COLORS = [
    (0, 255, 0),
    (0, 255, 255),
    (255, 0, 255),
    (255, 165, 0),
    (0, 165, 255),
    (255, 0, 0),
    (0, 0, 255),
    (255, 255, 0),
    (128, 255, 128),
    (128, 128, 255),
]

STAT_PRESETS = [
    ("cat_name",  "Select the CAT NAME text (e.g. 'William')"),
    ("cat_age",   "Select the AGE number (e.g. 'Age 10')"),
    ("cat_level", "Select the LEVEL text (e.g. 'Lv. 0')"),
    ("stat_str",  "Select the STRENGTH number (sword icon row)"),
    ("stat_dex",  "Select the DEXTERITY number (boot icon row)"),
    ("stat_con",  "Select the CONSTITUTION number (heart icon row)"),
    ("stat_int",  "Select the INTELLIGENCE number (brain icon row)"),
    ("stat_spd",  "Select the SPEED number (wing/boot icon row)"),
    ("stat_cha",  "Select the CHARISMA number (cat face icon row)"),
    ("stat_lck",  "Select the LUCK number (star icon row)"),
]


class RegionAnnotator:
    def __init__(self, image_path: str) -> None:
        self.original = cv2.imread(image_path)
        if self.original is None:
            print(f"ERROR: cannot read {image_path}")
            sys.exit(1)
        self.h, self.w = self.original.shape[:2]
        self.first_point: tuple[int, int] | None = None
        self.regions: list[dict] = []
        self.preset_idx = 0
        self.zoom = False
        self.mx = 0
        self.my = 0

    @property
    def _current_preset(self) -> str:
        if self.preset_idx < len(STAT_PRESETS):
            return STAT_PRESETS[self.preset_idx][0]
        return f"region_{len(self.regions)}"

    @property
    def _current_hint(self) -> str:
        if self.preset_idx < len(STAT_PRESETS):
            return STAT_PRESETS[self.preset_idx][1]
        return "Click two corners to define a custom region"

    def _draw(self) -> np.ndarray:
        canvas = self.original.copy()

        # Draw saved regions
        for i, reg in enumerate(self.regions):
            color = COLORS[i % len(COLORS)]
            x, y, rw, rh = reg["rect"]
            cv2.rectangle(canvas, (x, y), (x + rw, y + rh), color, 2)
            label = reg["name"]
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(canvas, (x, y - th - 6), (x + tw + 4, y), color, -1)
            cv2.putText(canvas, label, (x + 2, y - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        # Draw in-progress rectangle
        if self.first_point is not None:
            p = self.first_point
            cv2.circle(canvas, p, 4, (0, 0, 255), -1)
            cv2.rectangle(canvas, p, (self.mx, self.my), (0, 0, 255), 1)

        # Crosshair
        cv2.line(canvas, (self.mx, 0), (self.mx, self.h), (80, 80, 80), 1)
        cv2.line(canvas, (0, self.my), (self.w, self.my), (80, 80, 80), 1)

        # Coordinate display
        coord = f"({self.mx}, {self.my})"
        cv2.putText(canvas, coord, (self.mx + 10, self.my - 10),
                    cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255), 2)
        cv2.putText(canvas, coord, (self.mx + 10, self.my - 10),
                    cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 0), 1)

        # ── Top instruction banner ─────────────────────────────────
        banner_h = 52
        overlay = canvas[0:banner_h, :].copy()
        dark = np.zeros_like(overlay)
        cv2.addWeighted(dark, 0.7, overlay, 0.3, 0, overlay)
        canvas[0:banner_h, :] = overlay

        step_num = len(self.regions) + 1
        next_name = self._current_preset
        hint = self._current_hint
        color_next = COLORS[len(self.regions) % len(COLORS)]

        cv2.putText(canvas, f"Step {step_num}: [{next_name}]", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color_next, 2)
        cv2.putText(canvas, hint, (10, 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

        if self.first_point is None:
            cv2.putText(canvas, ">> Click TOP-LEFT corner", (self.w - 280, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
        else:
            cv2.putText(canvas, ">> Click BOTTOM-RIGHT corner", (self.w - 310, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # ── Bottom status bar ─────────────────────────────────────
        bar_h = 30
        cv2.rectangle(canvas, (0, self.h - bar_h), (self.w, self.h), (40, 40, 40), -1)

        status = f"Saved: {len(self.regions)}/{len(STAT_PRESETS)}  |  N/P: cycle name  |  Z: zoom  |  U: undo  |  S: save  |  Q: quit"
        cv2.putText(canvas, status, (8, self.h - 9),
                    cv2.FONT_HERSHEY_PLAIN, 1.0, (180, 180, 180), 1)

        # Zoom lens
        if self.zoom:
            radius = 80
            zx = max(radius, min(self.mx, self.w - radius))
            zy = max(radius, min(self.my, self.h - radius))
            crop = self.original[zy - radius:zy + radius, zx - radius:zx + radius].copy()

            # Draw crosshair on zoom crop
            ch, cw = crop.shape[:2]
            cv2.line(crop, (cw // 2, 0), (cw // 2, ch), (0, 0, 255), 1)
            cv2.line(crop, (0, ch // 2), (cw, ch // 2), (0, 0, 255), 1)

            zoomed = cv2.resize(crop, (radius * 4, radius * 4), interpolation=cv2.INTER_NEAREST)
            zh, zw = zoomed.shape[:2]
            x_off = self.w - zw - 5
            y_off = 5
            if x_off > 0 and y_off + zh < self.h - bar_h:
                canvas[y_off:y_off + zh, x_off:x_off + zw] = zoomed
                cv2.rectangle(canvas, (x_off, y_off), (x_off + zw, y_off + zh), (255, 255, 255), 2)

        return canvas

    def _on_mouse(self, event: int, x: int, y: int, flags: int, param: object) -> None:
        self.mx = x
        self.my = y

        if event == cv2.EVENT_LBUTTONDOWN:
            if self.first_point is None:
                self.first_point = (x, y)
            else:
                p1 = self.first_point
                rx = min(p1[0], x)
                ry = min(p1[1], y)
                rw = abs(x - p1[0])
                rh = abs(y - p1[1])

                if rw < 3 or rh < 3:
                    self.first_point = None
                    return

                name = self._current_preset
                allowlist = "0123456789" if name.startswith("stat_") else ""

                self.regions.append({
                    "name": name,
                    "rect": [rx, ry, rw, rh],
                    "allowlist": allowlist,
                    "preprocess": ["grayscale", "threshold"],
                })
                self.preset_idx += 1
                self.first_point = None

        elif event == cv2.EVENT_RBUTTONDOWN:
            self.first_point = None

    def run(self) -> None:
        win = "Mewgent Region Annotator"
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win, min(self.w * 2, 1920), min(self.h * 2, 1080))
        cv2.setMouseCallback(win, self._on_mouse)

        while True:
            canvas = self._draw()
            cv2.imshow(win, canvas)
            key = cv2.waitKey(30) & 0xFF

            if key == ord("q") or key == 27:
                break
            elif key == ord("s"):
                self._save()
                break
            elif key == ord("u"):
                if self.first_point is not None:
                    self.first_point = None
                elif self.regions:
                    removed = self.regions.pop()
                    self.preset_idx = max(0, self.preset_idx - 1)
            elif key == ord("z"):
                self.zoom = not self.zoom
            elif key == ord("n") or key == 82:  # N or arrow-up
                self.preset_idx = (self.preset_idx + 1) % len(STAT_PRESETS)
            elif key == ord("p") or key == 84:  # P or arrow-down
                self.preset_idx = max(0, self.preset_idx - 1)

        cv2.destroyAllWindows()

    def _save(self) -> None:
        if not self.regions:
            print("No regions defined — nothing to save.")
            return

        # Save annotated image
        canvas = self.original.copy()
        for i, reg in enumerate(self.regions):
            color = COLORS[i % len(COLORS)]
            x, y, rw, rh = reg["rect"]
            cv2.rectangle(canvas, (x, y), (x + rw, y + rh), color, 2)
            label = f"{reg['name']} [{x},{y},{rw},{rh}]"
            cv2.putText(canvas, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        out_img = Path("debug_screenshots/annotated_regions.png")
        cv2.imwrite(str(out_img), canvas)
        print(f"Annotated image -> {out_img}")

        # Build and write YAML
        yaml_data = {
            "game_resolution": [self.w, self.h],
            "scene_templates": {
                "cat_stats_screen": {
                    "file": "templates/cat_stats_header.png",
                    "match_threshold": 0.80,
                    "match_region": [0, 0, 400, 100],
                }
            },
            "regions": {},
        }
        for reg in self.regions:
            yaml_data["regions"][reg["name"]] = {
                "rect": reg["rect"],
                "allowlist": reg["allowlist"],
                "preprocess": reg["preprocess"],
            }

        yaml_path = Path("config/regions.yaml")
        yaml_str = yaml.dump(yaml_data, default_flow_style=False, sort_keys=False)
        yaml_path.write_text(yaml_str, encoding="utf-8")

        print(f"Regions YAML -> {yaml_path}")
        print(f"Defined {len(self.regions)} regions:")
        for reg in self.regions:
            print(f"  {reg['name']}: {reg['rect']}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tools/annotate_regions.py <screenshot.png>")
        sys.exit(1)
    RegionAnnotator(sys.argv[1]).run()


if __name__ == "__main__":
    main()
