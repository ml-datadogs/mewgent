"""Mock save watcher that emits realistic fake SaveData for dev-ui mode.

Provides a fully populated SaveData so every overlay widget has data to render
without needing a real Mewgenics .sav file.
"""
from __future__ import annotations

import random

from PySide6.QtCore import QObject, QTimer, Signal

from src.data.save_reader import SaveCat, SaveData

_CAT_NAMES = [
    "Mittens", "Whiskers", "Chairman Meow", "Purrlock Holmes",
    "Catrick Swayze", "Clawdia", "Sir Fluffington", "Mewton",
    "Pawcasso", "Catanova", "Furrdinand", "Meowzart",
    "Cleo", "Gizmo", "Noodle", "Biscuit",
]

_CLASSES = [
    "Fighter", "Hunter", "Mage", "Medic", "Tank", "Thief", "Necromancer",
    "Tinkerer", "Butcher", "Druid", "Psychic", "Monk",
]

_ABILITIES = [
    "Fireball", "IceBlast", "HealingTouch", "ShadowStrike",
    "ShieldBash", "PoisonBite", "Resurrect", "TrapSet",
    "Bullseye", "MegaBlast", "CraftArrow", "Brainstorm",
    "Seppuku", "WolfClaws", "Reposition", "Blizzard",
]

_PASSIVES = [
    "NineLives", "CatReflexes", "ThickFur", "NightVision",
    "Purrsistence", "SharpClaws", "SoftPaws", "Curiosity",
    "ThickSkull", "EternalHealth", "MadVisage", "PawMissile",
]


def _random_stat() -> int:
    return random.randint(3, 7)


def _make_mock_cats(count: int = 12) -> list[SaveCat]:
    cats: list[SaveCat] = []
    for i in range(count):
        name = _CAT_NAMES[i % len(_CAT_NAMES)]
        if i >= len(_CAT_NAMES):
            name = f"{name} Jr."
        cat = SaveCat(
            db_key=i + 1,
            name=name,
            level=random.randint(1, 30),
            age=random.randint(1, 9),
            gender=random.choice(["male", "female"]),
            active_class=random.choice(_CLASSES),
            base_str=_random_stat(),
            base_dex=_random_stat(),
            base_con=_random_stat(),
            base_int=_random_stat(),
            base_spd=_random_stat(),
            base_cha=_random_stat(),
            base_lck=_random_stat(),
            abilities=random.sample(_ABILITIES, k=random.randint(1, 3)),
            passives=random.sample(_PASSIVES, k=random.randint(0, 2)),
            status="in_house" if i < 8 else random.choice(["historical", "dead"]),
        )
        cats.append(cat)
    return cats


def _make_mock_save_data() -> SaveData:
    cats = _make_mock_cats(14)
    house_keys = {c.db_key for c in cats if c.status == "in_house"}
    return SaveData(
        cats=cats,
        house_cat_keys=house_keys,
        unlocked_classes=list(_CLASSES),
        unlocked_abilities=list(_ABILITIES),
        unlocked_passives=list(_PASSIVES),
        current_day=random.randint(5, 120),
        house_gold=random.randint(50, 9999),
        house_food=random.randint(10, 500),
        owner_steamid="MOCK_DEV",
        save_path="<mock>",
    )


class MockSaveWatcher(QObject):
    """Drop-in replacement for SaveWatcher that emits mock data on start."""

    save_updated = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._emit)

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def wait(self, _timeout_ms: int = 0) -> None:
        pass

    def _emit(self) -> None:
        self.save_updated.emit(_make_mock_save_data())
