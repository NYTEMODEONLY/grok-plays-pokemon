from PIL import Image, ImageDraw, ImageFont
import os

# Create directory if it doesn't exist
os.makedirs('static/img', exist_ok=True)

# Create a blank image with Game Boy dimensions (160x144)
img = Image.new('RGB', (160, 144), color=(200, 200, 200))
draw = ImageDraw.Draw(img)

# Add text
draw.rectangle([0, 60, 160, 84], fill=(100, 100, 100))
draw.text((30, 65), "GROK PLAYS POKEMON", fill=(255, 255, 255))
draw.text((15, 100), "Waiting for game to start...", fill=(50, 50, 50))

# Add border to simulate Game Boy screen
for i in range(3):
    draw.rectangle([i, i, 159-i, 143-i], outline=(50, 50, 50), width=1)

# Save the image
img.save('static/img/loading.png')
print("Loading image created at static/img/loading.png") 