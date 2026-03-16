"""Parse house_state to get the exact list of cats currently in the house."""

import os
import sqlite3
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import lz4.block

DB = os.environ["APPDATA"] + r"\Glaiel Games\Mewgenics\76561198103052764\saves\steamcampaign03.sav"
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Get house_state
cur.execute("SELECT data FROM files WHERE key = 'house_state'")
hs = cur.fetchone()[0]

# Parse the structure - each entry seems to be 52 bytes apart
# The cat keys appear at offsets: 4, 60, 112, 164, 216, 268, 320, 372, 424, 476, 528, 580, 632, 684, 736, 788, 840, 892, 944, 996
# That's offset 4, then every 52 bytes

# Let me figure out the exact structure
# First u32 = 0 (or count)
# Then repeating records of 52 bytes each containing a cat key

# Actually let me just extract all i32 values at positions where we found cat keys
# From the earlier scan, the cat key positions were:
# 4, 60, 112, 164, 216, 268, 320, 372, 424, 476, 528, 580, 632, 684, 736, 788, 840, 892, 944, 996
# Stride = 52 bytes

first_u32 = struct.unpack_from("<I", hs, 0)[0]
print(f"house_state: {len(hs)} bytes, first_u32={first_u32}")

# Extract cat keys at stride 52, starting at offset 4
house_cat_keys = []
offset = 4
while offset + 4 <= len(hs):
    val = struct.unpack_from("<I", hs, offset)[0]
    if val == 0:
        break
    # Check if it's a plausible cat key
    if 1 <= val <= 500:
        house_cat_keys.append(val)
    offset += 52

print(f"\nFound {len(house_cat_keys)} house cats")
print(f"Keys: {house_cat_keys}")

# Also let me dump the full structure of one record
print(f"\n=== First house_state record (52 bytes from offset 4) ===")
rec = hs[4:56]
for i in range(0, len(rec), 4):
    val = struct.unpack_from("<I", rec, i)[0]
    fval = struct.unpack_from("<f", rec, i)[0]
    raw = rec[i:i+4].hex()
    # Also try as f64 at 8-byte boundaries
    f64_str = ""
    if i % 8 == 0 and i + 8 <= len(rec):
        f64 = struct.unpack_from("<d", rec, i)[0]
        f64_str = f"  f64={f64:.4f}"
    print(f"  @{i:3d}: {raw}  u32={val:12d}  f32={fval:.4f}{f64_str}")

# Now get the names for these keys
print(f"\n=== HOUSE CATS ({len(house_cat_keys)} total) ===")

# Get full names from name_gen_history_w
cur.execute("SELECT data FROM files WHERE key = 'name_gen_history_w'")
history = cur.fetchone()[0]
pos = 8
name_count = struct.unpack_from("<Q", history, 0)[0]
all_names = {}
for i in range(name_count):
    nlen = struct.unpack_from("<Q", history, pos)[0]
    pos += 8
    nname = history[pos:pos + nlen * 2].decode("utf-16-le")
    pos += nlen * 2
    all_names[i + 1] = nname

for key in house_cat_keys:
    name = all_names.get(key, "?")
    # Also get level/class from cat blob
    cur.execute("SELECT data FROM cats WHERE key = ?", (key,))
    row = cur.fetchone()
    if row and row[0]:
        blob = row[0]
        size = struct.unpack_from("<I", blob, 0)[0]
        flat = lz4.block.decompress(blob[4:], uncompressed_size=size)
        
        # Find strings to get level/age
        nlen = struct.unpack_from("<q", flat, 12)[0]
        strings = []
        p = 20 + nlen * 2
        while p + 8 < len(flat):
            slen = struct.unpack_from("<q", flat, p)[0]
            if 1 <= slen <= 60 and p + 8 + slen <= len(flat):
                try:
                    s = flat[p+8:p+8+slen].decode("ascii")
                    if s.isprintable():
                        strings.append((p, slen, s))
                        p += 8 + slen
                        continue
                except:
                    pass
            p += 1
        
        level = 0
        age = 0
        if len(strings) >= 2:
            s1_off = strings[1][0]
            if s1_off >= 8:
                level = struct.unpack_from("<i", flat, s1_off - 8)[0]
                age = struct.unpack_from("<i", flat, s1_off - 4)[0]
        
        cls = "?"
        for _, _, s in reversed(strings):
            if s in ("Fighter", "Hunter", "Mage", "Medic", "Tank", "Thief", 
                      "Necromancer", "Colorless", "robotom", "terminator", "Druid"):
                cls = s
                break
            if s == "None" or s == "Colorless":
                continue
        
        print(f"  #{key:3d}  {name:22s}  lv={level:2d}  age={age:2d}  class={cls}")

# Now count the categories
all_cat_keys = set()
cur.execute("SELECT key FROM cats")
for row in cur.fetchall():
    all_cat_keys.add(row[0])

house_set = set(house_cat_keys)
dead_keys = set()
alive_not_house = set()

for key in all_cat_keys:
    cur.execute("SELECT data FROM cats WHERE key = ?", (key,))
    blob = cur.fetchone()[0]
    size = struct.unpack_from("<I", blob, 0)[0]
    flat = lz4.block.decompress(blob[4:], uncompressed_size=size)
    
    nlen = struct.unpack_from("<q", flat, 12)[0]
    strings = []
    p = 20 + nlen * 2
    while p + 8 < len(flat):
        slen = struct.unpack_from("<q", flat, p)[0]
        if 1 <= slen <= 60 and p + 8 + slen <= len(flat):
            try:
                s = flat[p+8:p+8+slen].decode("ascii")
                if s.isprintable():
                    strings.append((p, slen, s))
                    p += 8 + slen
                    continue
            except:
                pass
        p += 1
    
    age = 0
    if len(strings) >= 2:
        s1_off = strings[1][0]
        if s1_off >= 4:
            age = struct.unpack_from("<i", flat, s1_off - 4)[0]
    
    if key in house_set:
        pass  # already counted
    elif age == 0:
        dead_keys.add(key)
    else:
        alive_not_house.add(key)

print(f"\n=== SUMMARY ===")
print(f"  Total cats in DB: {len(all_cat_keys)}")
print(f"  In house right now: {len(house_set)}")
print(f"  Dead/lost (age=0): {len(dead_keys)}")
print(f"  Historical (alive but not in house): {len(alive_not_house)}")
print(f"  Deleted (gaps in keys): 5")

conn.close()
