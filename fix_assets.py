# fix_assets.py
from pathlib import Path
from shutil import copyfile

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
TARGET = ASSETS / "ai_hero.png"

print("Project root:", ROOT.resolve())
print("Assets folder:", ASSETS.resolve())

if not ASSETS.exists():
    print("➡️ assets folder does not exist. Creating it now.")
    ASSETS.mkdir(parents=True, exist_ok=True)

# If target already exists, report and exit
if TARGET.exists():
    print("✅ Target already exists:", TARGET.resolve())
    print("size:", TARGET.stat().st_size, "bytes")
    raise SystemExit(0)

# List files in assets and show raw names
files = list(ASSETS.iterdir())
print("\nFiles currently in assets:")
for f in files:
    print(" -", repr(f.name), "(suffix:", f.suffix, ")")

# Try to find the best candidate to rename/copy to ai_hero.png
candidates = []
# prefer files with ai_hero in name
for f in files:
    name_lower = f.name.lower()
    if "ai_hero" in name_lower or "ai-hero" in name_lower or "aihero" in name_lower:
        candidates.append(f)
# fallback: any image-like file
if not candidates:
    for f in files:
        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            candidates.append(f)

if not candidates:
    print("\n❌ No candidate image files found in assets to rename/copy.")
    print("If you have the image elsewhere, move it into the assets folder and name it exactly ai_hero.png")
    raise SystemExit(1)

# pick best candidate (prefer png)
best = None
for f in candidates:
    if f.suffix.lower() == ".png":
        best = f
        break
if best is None:
    best = candidates[0]

print("\nUsing candidate:", repr(best.name), "-> will make", TARGET.name)

# If candidate already named exactly ai_hero.png but exists() was False earlier, just copy to ensure proper name
try:
    # attempt rename first (safe if not open)
    best.rename(TARGET)
    print("✅ Renamed file to:", TARGET.resolve())
except Exception as e:
    print("⚠️ Rename failed:", e)
    print("Trying to copy instead...")
    try:
        copyfile(str(best), str(TARGET))
        print("✅ Copied file to:", TARGET.resolve())
    except Exception as e2:
        print("❌ Copy also failed:", e2)
        raise SystemExit(1)

print("\nDone. Now run: streamlit run app.py")
