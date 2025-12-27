from PIL import Image
import os

# Создай папку resized, если нужно
os.makedirs('resized', exist_ok=True)

for name in ['play.png', 'pause.png']:
    path = os.path.join('icons', name)
    if not os.path.exists(path):
        print(f"Нет файла: {path}")
        continue
    try:
        img = Image.open(path)
        img_resized = img.resize((300, 300), Image.Resampling.LANCZOS)
        img_resized.save(os.path.join('resized', name))
    except Exception as e:
        print(f"Ошибка: {e}")

