"""Test the SaveReader against the actual save file."""

import os
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.data.save_reader import find_save_files, read_save  # noqa: E402

# Find saves
saves = find_save_files()
print(f"Found {len(saves)} save file(s):")
for s in saves:
    print(f"  {s}")

if not saves:
    print("No save files found!")
    sys.exit(1)

# Read the main save
save = read_save(saves[0])
print(f"\nSave: {save.save_path}")
print(f"Day: {save.current_day}")
print(f"Gold: {save.house_gold}")
print(f"Food: {save.house_food}")
print(f"Steam ID: {save.owner_steamid}")
print(f"Cats: {len(save.cats)}")

# Print cat table
print(
    f"\n{'Key':>4} {'Name':22s} {'Lv':>3} {'Age':>4} {'Gender':>6} {'Class':12s} "
    f"{'STR':>4} {'DEX':>4} {'CON':>4} {'INT':>4} {'SPD':>4} {'CHA':>4} {'LCK':>4}  Abilities"
)
print("-" * 130)

for cat in save.cats[:50]:
    abilities_str = ", ".join(cat.abilities[:3])
    if len(cat.abilities) > 3:
        abilities_str += f" (+{len(cat.abilities) - 3})"
    print(
        f"{cat.db_key:4d} {cat.name:22s} {cat.level:3d} {cat.age:4d} {cat.gender:>6s} {cat.active_class:12s} "
        f"{cat.base_str:4d} {cat.base_dex:4d} {cat.base_con:4d} {cat.base_int:4d} "
        f"{cat.base_spd:4d} {cat.base_cha:4d} {cat.base_lck:4d}  {abilities_str}"
    )

# Specific cats to validate
print("\n\n=== VALIDATION: Known cats ===\n")
known_cats = {
    "Dingle": {"str": 5, "dex": 6, "con": 7},  # base stats from screenshot
    "Enzo": {},
    "Sloane": {},
    "Greifi": {},
    "Moiraine": {},
}
for cat in save.cats:
    if cat.name in known_cats:
        print(f"{cat.name}:")
        print(
            f"  Level={cat.level}, Age={cat.age}, Gender={cat.gender}, Class={cat.active_class}"
        )
        print(
            f"  Stats: STR={cat.base_str} DEX={cat.base_dex} CON={cat.base_con} "
            f"INT={cat.base_int} SPD={cat.base_spd} CHA={cat.base_cha} LCK={cat.base_lck}"
        )
        print(f"  Abilities: {cat.abilities}")

        if cat.name == "Dingle":
            expected = known_cats["Dingle"]
            for stat, exp in expected.items():
                actual = getattr(cat, f"base_{stat}")
                match = "OK" if actual == exp else f"MISMATCH (expected {exp})"
                print(f"  Validate base_{stat}: {actual} {match}")

# Summary stats
total_with_stats = sum(1 for c in save.cats if c.base_str > 0 or c.base_dex > 0)
total_with_class = sum(1 for c in save.cats if c.active_class not in ("", "None"))
total_with_gender = sum(1 for c in save.cats if c.gender)
print("\nSummary:")
print(f"  Cats with non-zero stats: {total_with_stats}/{len(save.cats)}")
print(f"  Cats with active class: {total_with_class}/{len(save.cats)}")
print(f"  Cats with gender: {total_with_gender}/{len(save.cats)}")
