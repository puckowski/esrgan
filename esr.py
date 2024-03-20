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

def replace_high_rgb_with_transparent(image_path):
    # Open the image
    image = Image.open(image_path)
    
    # Convert the image to RGBA mode (if not already)
    image = image.convert("RGBA")
    
    # Get the width and height of the image
    width, height = image.size
    
    # Iterate through each pixel
    for x in range(width):
        for y in range(height):
            # Get the RGBA values of the current pixel
            r, g, b, a = image.getpixel((x, y))
            
            # Check if red, green, and blue values are greater than 200
            if r > 200 and g > 200 and b > 200:
                # Replace the pixel with fully transparent
                image.putpixel((x, y), (0, 0, 0, 0))
    
    # Save the modified image
    image.save(image_path)

def has_fully_transparent_pixels(image_path):
    # Open the image
    image = Image.open(image_path)
    
    # Convert the image to RGBA mode (if not already)
    image = image.convert("RGBA")
    
    # Get the width and height of the image
    width, height = image.size
    
    # Iterate through each pixel
    for x in range(width):
        for y in range(height):
            # Get the RGBA values of the current pixel
            r, g, b, a = image.getpixel((x, y))
            
            # Check if the alpha channel value is 0 (fully transparent)
            if a == 0:
                return True  # Fully transparent pixel found
    
    # No fully transparent pixel found
    return False

def has_partial_transparent_pixels(image_path):
    # Open the image
    image = Image.open(image_path)
    
    # Convert the image to RGBA mode (if not already)
    image = image.convert("RGBA")
    
    # Get the width and height of the image
    width, height = image.size
    
    # Iterate through each pixel
    for x in range(width):
        for y in range(height):
            # Get the RGBA values of the current pixel
            r, g, b, a = image.getpixel((x, y))
            
            # Check if the alpha channel value is greater than 0 and less than 255
            if 0 < a < 255:
                return True  # Partially transparent pixel found
    
    # No partially transparent pixel found
    return False

def has_white_pixel(image_path):
    # Open the image
    image = Image.open(image_path)
    
    # Convert the image to RGB mode (if not already)
    image = image.convert("RGB")
    
    # Get the width and height of the image
    width, height = image.size
    
    # Iterate through each pixel
    for x in range(width):
        for y in range(height):
            # Get the RGB values of the current pixel
            r, g, b = image.getpixel((x, y))
            
            # Check if the pixel is white (R, G, and B values are all 255)
            if r == 255 and g == 255 and b == 255:
                return True  # White pixel found
    
    # No white pixel found
    return False

def webui(arg1, arg2):
    load_upscalers()

    upscaler = UpscalerESRGAN(dirname=".")

    has_white = has_white_pixel(arg1)
    has_fully_transparent = has_fully_transparent_pixels(arg1)

    if has_fully_transparent and not has_white:
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

        tmp_filename = arg1 + "_tmp.png"
        image.save(tmp_filename)

        image = Image.open(tmp_filename)
        image  = image.convert('RGB')

        # upscale the image using RealESRGAN
        upscaled_image = upscaler.do_upscale(image, selected_model=".\\models\\ESRGAN\\ESRGAN_4x.pth")

        # save the upscaled image
        upscaled_image.save(arg2)

        # Example usage
        replace_high_rgb_with_transparent(arg2)
        
        print("done:" + arg2)
    elif has_partial_transparent_pixels(arg1):
        print("could not process; partially transparent: " + arg1)
    elif not has_fully_transparent:
        # load an image to upscale
        image = Image.open(arg1)
        image  = image.convert('RGB')

        # upscale the image using RealESRGAN
        upscaled_image = upscaler.do_upscale(image, selected_model=".\\models\\ESRGAN\\ESRGAN_4x.pth")

        # save the upscaled image
        upscaled_image.save(arg2)

        print("done:" + arg2)
    else:
        print("could not process; may be white pixels: " + arg1)
        

if __name__ == "__main__":
    webui(str(sys.argv[1]), str(sys.argv[2]))