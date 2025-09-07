import os
from PIL import Image
import glob
from tqdm import tqdm

import imageio.v2 as imageio
import os

def generate_gif_PIL(folder_path, output_gif="output.gif", duration=100, loop=0):
    """
    Creates a GIF from sequentially numbered JPG files in a folder.

    Args:
        folder_path (str): Path to the folder containing JPG files
        output_gif (str): Name of the output GIF file
        duration (int): Time between frames in milliseconds
        loop (int): Number of loops (0 = infinite)
    """
    # Get all jpg files in the folder and sort them numerically
    png_files = sorted(
        glob.glob(os.path.join(folder_path, "*.png")),
        key=lambda x: int(os.path.splitext(os.path.basename(x))[0])
    )

    if not png_files:
        print(f"No png files found in {folder_path}")
        return

    # Open all images and store in a list
    images = []
    for i, file in tqdm(enumerate(png_files)):
        try:
            img = Image.open(file)
            images.append(img)
            #clear_output(wait=True)
        except Exception as e:
            print(f"Error loading {file}: {e}")

    if not images:
        print("No valid images found")
        return

    # Save as GIF
    print("Saving GIF...")
    images[0].save(
        output_gif,
        save_all=True,
        append_images=images[1:],
        duration=duration,
        loop=loop,
        optimize=True,
    )

    print(f"GIF created successfully: {os.path.join(folder_path, output_gif)}")




# Folder containing PNGs (e.g., 001.png, 002.png, ...)
def generate_gif_imageio(png_folder, save_path, fps):

    images = sorted([
        img for img in os.listdir(png_folder)
        if img.endswith(".png") and img.split(".")[0].isdigit()
    ], key=lambda x: int(x.split(".")[0]))  # Sort by numeric part

    # Create GIF (fastest settings)
    with imageio.get_writer(
        save_path,
        mode='I',
        #duration=0.1,  # Time per frame (seconds)
        fps=fps,        # Frames per second (overrides duration if set)
    ) as writer:
        for filename in images:
            image = imageio.imread(os.path.join(png_folder, filename))
            writer.append_data(image)


def clear_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # Remove files and links
            # elif os.path.isdir(file_path):  # Uncomment to also remove subdirectories
            #     shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')



import os
import subprocess
from typing import Optional

def pngs_to_video(
    input_folder: str,
    output_video: str = "output.mp4",
    frame_rate: int = 30,
    start_number: int = 1,
    input_format: str = "%04d.png",
    overwrite: bool = True,
    ffmpeg_path: str = "D:/Programme/ffmpeg/",
) -> str:
    """
    Convert a sequence of PNG files in a folder to a video using ffmpeg.

    Args:
        input_folder (str): Path to the folder containing PNG files.
        output_video (str): Output video filename (default: "output.mp4").
        frame_rate (int): Frame rate of the output video (default: 30).
        start_number (int): Starting number of the sequence (default: 1).
        input_format (str): Format of the input filenames (default: "%04d.png").
                           Example: "%04d.png" matches "0001.png", "0002.png", etc.
        overwrite (bool): Overwrite output file if it exists (default: True).
        ffmpeg_path (Optional[str]): Custom path to ffmpeg executable (default: None, uses system ffmpeg).

    Returns:
        str: Path to the generated video file.

    Raises:
        FileNotFoundError: If ffmpeg is not found or input folder does not exist.
        subprocess.CalledProcessError: If ffmpeg command fails.
    """
    # Check if input folder exists
    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

    # Construct ffmpeg command
    ffmpeg_cmd = [
        ffmpeg_path if ffmpeg_path else "ffmpeg",
        "-y" if overwrite else "-n",  # Overwrite output file if exists
        "-framerate", str(frame_rate),
        "-start_number", str(start_number),
        "-i", os.path.join(input_folder, input_format),
        "-c:v", "libx264",  # H.264 codec
        "-pix_fmt", "yuv420p",  # Compatibility with most players
        "-vf", "fps=30",  # Ensure output frame rate
        "-loglevel", "error",  # Suppress unnecessary logs
        output_video,
    ]

    # Run ffmpeg command
    try:
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"Video successfully created: {output_video}")
        return output_video
    except subprocess.CalledProcessError as e:
        raise subprocess.CalledProcessError(
            e.returncode, e.cmd, f"ffmpeg command failed: {e.stderr}"
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            "ffmpeg not found. Please install ffmpeg and ensure it is in your PATH."
        )

