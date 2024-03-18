import importlib
from PIL import Image
import sys

from modules.esrgan_model import UpscalerESRGAN

def load_upscalers():
    # We can only do this 'magic' method to dynamically load upscalers if they are referenced,
    # so we'll try to import any _model.py files before looking in __subclasses__
    full_model = f"modules.esrgan_model"
    try:
        importlib.import_module(full_model)
    except:
        pass

def webui(arg1, arg2):
    load_upscalers()

    upscaler = UpscalerESRGAN(dirname=".")

    # load an image to upscale
    image = Image.open(arg1)
    image  = image.convert('RGBA')

    # Get image dimensions
    width, height = image.size

    # Loop through all pixels
    for x in range(width):
        for y in range(height):
            # Get pixel and its alpha value
            pixel = image.getpixel((x, y))
            alpha = pixel[3]

            # Check if pixel is fully transparent
            if alpha == 0:
                # Replace fully transparent pixel with white
                image.putpixel((x, y), (255, 255, 255, 255))  # RGBA value for white

    image.save("tmp.png")

    image = Image.open("tmp.png")
    image  = image.convert('RGB')

    # upscale the image using RealESRGAN
    upscaled_image = upscaler.do_upscale(image, selected_model=".\\models\\ESRGAN\\ESRGAN_4x.pth")

    # save the upscaled image
    upscaled_image.save(arg2)

    print(str(arg1))
    print(str(arg2))
        

if __name__ == "__main__":
    webui(str(sys.argv[1]), str(sys.argv[2]))