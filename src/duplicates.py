import os
import shutil
from itertools import combinations
import hashlib
from PIL import Image
import numpy as np
import cv2
from datetime import datetime
from configparser import ConfigParser
from . import fixer_util
from .ffprobe import FFProbe

def __generate_file_hash(file_path: str):
    BUF_SIZE = 65536
    hasher = hashlib.sha256()
    
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            hasher.update(data)
            
    return hasher.hexdigest()

def __generate_image_hash(file_path: str):
    try:
        # Open the image file
        img = Image.open(file_path)
        
        # Create a hash object using the SHA256 algorithm
        hash_obj = hashlib.sha256()
        
        # Get the pixel data of the image and update the hash object
        pixel_data = img.tobytes()
        hash_obj.update(pixel_data)
        
        # Get the hexadecimal digest of the hash object
        img_hash = hash_obj.hexdigest()
        
        return img_hash
    except Exception as e:
        with open("report.txt", "a") as f:
            print(f"An error occurred while generating an image hash: {str(e)}", file=f)
        print(f"An error occurred while generating an image hash: {str(e)}")
        return None

def __generate_video_shape(file_path: str):
    video_shape = ""

    try:
        metadata = FFProbe(file_path)

        video_streams = [s for s in metadata.streams if s.is_video()]
        if not video_streams:
            return None

        video_stream = video_streams[0]

        video_shape += str(video_stream.frames())
        video_shape += video_stream.width
        video_shape += video_stream.height

        return video_shape
    except Exception as e:
        with open("report.txt", "a") as f:
            print(f"An error occurred while generating a video shape: {str(e)}", file=f)
        print(f"An error occurred while generating a video shape: {str(e)}")
        return None

def __generate_video_hash(file_path: str):
    try:
        # Open the video file
        video = cv2.VideoCapture(file_path)

        # Create a hash object using the SHA256 algorithm
        hash_obj = hashlib.sha256()

        # Read and process the frames
        while True:
            ret, frame = video.read()

            # Break the loop if we have reached the end of the video
            if not ret:
                break

            # Get the pixel data of the frame and update the hash object
            pixel_data = frame.tobytes()
            hash_obj.update(pixel_data)

        # Release the video file
        video.release()

        # Get the hexadecimal digest of the hash object
        video_hash_value = hash_obj.hexdigest()

        return video_hash_value
    except Exception as e:
        with open("report.txt", "a") as f:
            print(f"An error occurred while generating a video hash: {str(e)}", file=f)
        print(f"An error occurred while generating a video hash: {str(e)}")
        return None

def __find_duplicate_files(*paths, heavy=True):
    file_hashes = {}
    video_shapes = {}
    
    for path in paths:
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                file_type = fixer_util.guess_media_type(file)
                file_hash = None
                video_shape = None

                try:
                    # try to get a hash of the image content
                    if file_type == "image":
                        file_hash = __generate_image_hash(file_path)
                        
                        # if no img hash could be generated, maybe it is a 
                        # mis-labeled video so try to get the file's video shape 
                        if not file_hash:
                            video_shape = __generate_video_shape(file_path)

                    # try to get a shape of the video centent
                    if file_type == "video":
                        video_shape = __generate_video_shape(file_path)
                        
                        # if no video shape could be generated, maybe it is a 
                        # mis-labeled image so try to get the file's image 
                        # content hash
                        if not video_shape:
                            file_hash = __generate_image_hash(file_path)

                    # if no video shape or image hash was found, we dunno what 
                    # the heck this file is, so just take a hash of the whole 
                    # thing
                    if not file_hash and not video_shape:
                        file_hash = __generate_file_hash(file_path)

                except OSError as e:
                    continue
                
                # add the img or file hash to the list of hashes
                if file_hash in file_hashes:
                    file_hashes[file_hash].append(file_path)
                elif file_hash:
                    file_hashes[file_hash] = [file_path]
                
                # add the video shape to the list of video shapes
                if video_shape in video_shapes:
                    video_shapes[video_shape].append(file_path)
                elif video_shape:
                    video_shapes[video_shape] = [file_path]

    similiar_video_groups = [tuple(videos) for videos in video_shapes.values() if len(videos) > 1]

    # since video shape is not a good measure of uniqueness, hash all videos
    # with the same shape
    video_hashes = {}

    for video_group in similiar_video_groups:
        for file_path in video_group:
            video_hash = None

            try:
                video_hash = __generate_video_hash(file_path)
            except OSError as e:
                continue
            
            # add the video hash to the list of hashes
            if video_hash in video_hashes:
                video_hashes[video_hash].append(file_path)
            elif video_hash:
                video_hashes[video_hash] = [file_path]
                    
    duplicate_videos = [tuple(videos) for videos in video_hashes.values() if len(videos) > 1]
    duplicate_images = [tuple(files) for files in file_hashes.values() if len(files) > 1]

    return duplicate_images + duplicate_videos

def generate_report(start_path, config: ConfigParser):
    print(datetime.now(), "Generating duplicate file report ... ")
    heavy = config.get("settings", "heavy_duplicate_file_checking")
    dups = __find_duplicate_files(start_path, heavy=heavy)
    with open("duplicates.txt", "w") as fi:
        for dup in dups:
            print('"', '","'.join(dup), '"', file=fi, sep="")

    return dups

def move_older(duplicate_tuples: list, config: ConfigParser):
    with open("report.txt", "a") as f:
        print(datetime.now(), "Moving duplicate files ... ", file=f)
    print(datetime.now(), "Moving duplicate files ... ")
    dest_dir = config.get("settings", "duplicate_path")
    preferred_keyword = config.get("settings", "preferred_keyword_in_dups")
    unpreferred_keyword = config.get("settings", "unpreferred_keyword_in_dups")

    fixer_util.create_directories(dest_dir + "/d")
    moved_files = []

    for duplicate_files in duplicate_tuples:
        if not duplicate_files:
            continue

        # Find the file with the newest system modification date. If the files 
        # have the same date, prefer the file with the smallest file name to get
        # rid of common "(1)" or "- Copy" postfixes in file names. If the files
        # have the same modificatin date and same filename length, then prefer 
        # files that have the passed preferred keywords in them, then prefer 
        # files that don't have the unpreferred keyword in them. If all of those 
        # conditions are the same, then prefer the file with the least amount of 
        # digits at the end of the file. This will move files that an increment 
        # added to their nonce in the output of this program.
        def file_criteria(file_name: str):
            mtime = os.path.getmtime(file_name)
            name = os.path.basename(file_name)
            last_7_chars_digit_count = sum(c.isdigit() for c in name[-7:])
            return (
                mtime, 
                -len(name), 
                preferred_keyword in file_name, 
                not unpreferred_keyword in file_name, 
                -last_7_chars_digit_count
            )

        preferred_file = max(duplicate_files, key=file_criteria)

        # Move the other files to the destination directory
        for file in duplicate_files:
            if file != preferred_file:
                try:
                    dest_file_path = os.path.join(dest_dir, os.path.basename(file))
                    shutil.move(file, dest_file_path)
                    moved_files.append((file, dest_file_path))
                except (OSError, shutil.Error) as e:
                    pass

    return moved_files
