import os
import subprocess

# List all files in the current directory
for file in os.listdir('.'):
    if file.endswith('.png'):
        # Apply the mogrify command
        subprocess.run(['mogrify', '-colorspace', 'gray', file], check=True)

        # Apply the toiftool command
        toif_file = file.replace('.png', '.toif')
        subprocess.run(['toiftool', 'convert', file, toif_file], check=True)

print("Commands applied to all .png files in the current directory.")
