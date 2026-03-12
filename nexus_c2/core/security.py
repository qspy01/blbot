import io
import random
from PIL import Image, ImageDraw

class SecurityEngine:
    @staticmethod
    def generate_stealth_image(code: str) -> io.BytesIO:
        width, height = 450, 200
        image = Image.new('RGB', (width, height), color=(15, 15, 15))
        draw = ImageDraw.Draw(image)
        for _ in range(20):
            x1, y1 = random.randint(0, width), random.randint(0, height)
            x2, y2 = random.randint(0, width), random.randint(0, height)
            draw.line([(x1, y1), (x2, y2)], fill=(40, 40, 40), width=1)
        draw.text((160, 90), f"SIGNAL: {code}", fill=(0, 255, 100))
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        buf.seek(0)
        return buf