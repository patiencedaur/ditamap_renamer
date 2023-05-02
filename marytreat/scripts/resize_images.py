import os, subprocess

"""
Requires ImageMagick installed.
"""

print("""
This script requires ImageMagick installed on your computer.
* Convert pngs with too large resolutions into 150 ppi.
* Convert too wide 150 ppi images to 4 inches wide (600 px).
  
It is recommended to backup the images folder before you run this script.

""")
images_folder = input('Enter the path to the images folder: ')

pngs = [fl for fl in os.listdir(images_folder) if fl.endswith(('.png', '.PNG'))]
too_large = []
reso_right_but_too_wide = []

print('Analyzing images...')


def magick_convert(image_list):
    for pngfile in image_list:
        try:
            magick_identify = ['magick', 'identify',
                               '-format', '%[resolution.x] %[width]',
                               '-units', 'PixelsPerInch',
                               os.path.join(images_folder, pngfile)]
            resolution, width = subprocess.run(magick_identify, capture_output=True, text=True).stdout.split(' ')
            if float(resolution) > 150 and float(width) > 70:  # filter out things like icons
                print('Converting', pngfile, 'to 150 ppi...')
                too_large.append((pngfile, resolution))
                magick_density = ['magick', 'mogrify',
                                  '-density', '150', '-units', 'PixelsPerInch',
                                  os.path.join(images_folder, pngfile)]
                subprocess.run(magick_density)
            if 148 < float(resolution) <= 150 and float(width) > 600:
                print('Converting', pngfile, 'to 4 inches wide...')
                reso_right_but_too_wide.append((pngfile, width))
                magick_resize = ['magick', 'mogrify',
                                 '-resize', '600',
                                 os.path.join(images_folder, pngfile)]
                subprocess.run(magick_resize)
        except Exception as e:
            print(e)


magick_convert(pngs)
magick_convert(pngs)  # The second run catches too-wide files that weren't 150 ppi in the first run

print()
print('Converted', len(too_large), 'files with resolution larger than 150.')
print('Converted', len(reso_right_but_too_wide), 'files that were wider than ~4 inches.')
