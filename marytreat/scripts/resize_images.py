from msvcrt import getch
import os
import subprocess

"""
Requires ImageMagick installed.
"""

print("""
This script requires ImageMagick installed on your computer.
* Convert local pngs with too large resolutions into 150 ppi.
* Convert too wide images:
  - 4.5 inches wide (675 px) for vertical
  - 2 inches wide for horizontal
  
It is recommended to backup the images folder before you run this script.

""")

images_folder = input('Enter the path to the local images folder: ')

try:
    pngs = [fl for fl in os.listdir(images_folder) if fl.endswith(('.png', '.PNG'))]
except FileNotFoundError as e:
    print(e)
    print('Press any key to exit.')
    getch()
    exit()

too_large = []
reso_right_but_too_wide = []


def magick_convert(image_list, dummy=False):
    """
    :param image_list: list of PNGs to analyze and convert
    :param dummy: for test runs
    """
    def analyze(fl):
        print('Analyzing {}...'.format(fl))
        magick_identify = ['magick', 'identify',
                           '-format', '%[resolution.x] %[width] %[height]',
                           '-units', 'PixelsPerInch',
                           os.path.join(images_folder, fl)]
        reso, w, h = subprocess.run(
            magick_identify, capture_output=True, text=True
        ).stdout.split(' ')
        return float(reso), float(w), float(h)

    def is_vertical(w, h):
        return h > (1.2 * w)

    def is_square(w, h):
        return (h <= (1.2 * w) and h >= (0.85 * w))

    for pngfile in image_list:
        try:
            resolution, width, height = analyze(pngfile)
            if resolution > 150 and width > 70:  # filter out things like icons
                too_large.append((pngfile, resolution))
                print('Converting', pngfile, 'to 150 ppi...')
                if not dummy:
                    magick_density = ['magick', 'mogrify',
                                      '-density', '150', '-units', 'PixelsPerInch',
                                      os.path.join(images_folder, pngfile)]
                    subprocess.run(magick_density)
            elif resolution < 148:
                continue

            if is_vertical(width, height) and width > 350:
                reso_right_but_too_wide.append((pngfile, width))
                print('Converting vertical', pngfile, 'to 2 inches wide...')
                if not dummy:
                    magick_resize = ['magick', 'mogrify',
                                     '-resize', '300',
                                     os.path.join(images_folder, pngfile)]
                    subprocess.run(magick_resize)
            
            elif not is_vertical(width, height) and width > 675:
                reso_right_but_too_wide.append((pngfile, width))
                print('Converting horizontal', pngfile, 'to 4.5 inches wide...')
                if not dummy:
                    magick_resize = ['magick', 'mogrify',
                                     '-resize', '675',
                                     os.path.join(images_folder, pngfile)]
                    subprocess.run(magick_resize)
                    
            elif is_square(width, height) and width > 500:
                reso_right_but_too_wide.append((pngfile, width))
                print('Converting square', pngfile, 'to 3 inches wide...')
                if not dummy:
                    magick_resize = ['magick', 'mogrify',
                                     '-resize', '450',
                                     os.path.join(images_folder, pngfile)]
                    subprocess.run(magick_resize)
        except Exception as e:
            print(e)


magick_convert(pngs)
# magick_convert(pngs)  # The second run catches too-wide files that weren't 150 ppi in the first run

print()
print('Converted', len(too_large), 'files with resolution larger than 150.')
print('Converted', len(reso_right_but_too_wide), 'files that were too wide.')

getch()
