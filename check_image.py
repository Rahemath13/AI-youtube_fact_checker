import os

hero_image_path = os.path.join(os.getcwd(), "assets", "ai_hero.png")

print("Looking for:", hero_image_path)
print("Exists?", os.path.exists(hero_image_path))

if not os.path.exists(hero_image_path):
    print("Files inside assets folder:")
    assets_path = os.path.join(os.getcwd(), "assets")
    if os.path.exists(assets_path):
        print(os.listdir(assets_path))
    else:
        print("Assets folder does NOT exist.")
