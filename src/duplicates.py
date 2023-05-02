import os
import shutil
from itertools import combinations
import hashlib
from PIL import Image
import numpy as np
import cv2
from datetime import datetime
from configparser import ConfigParser
from .fixer_util import create_directories

def __generate_file_hash(file_path):
    BUF_SIZE = 65536
    hasher = hashlib.sha256()
    
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            hasher.update(data)
            
    return hasher.hexdigest()

def __file_hashes_are_identical(file1_path, file2_path):
    if __generate_file_hash(file1_path) == __generate_file_hash(file2_path):
        return True
    return False

def __images_are_identical(img1_path, img2_path):
    try:
        img1 = Image.open(img1_path)
    except Exception as e:
        return False

    try:
        img2 = Image.open(img2_path)
    except Exception as e:
        return False

    try:
        return np.array_equal(img1, img2)
    except:
        return False

def __videos_are_identical(vid1_path, vid2_path):
    video_extensions = ["mp4", "avi", "mkv", "mov", "webm", "m4v", "3gp", "mpeg"]
    ext1 = vid1_path.split(".")[-1]
    
    if not ext1 in video_extensions:
        return False
    
    ext2 = vid2_path.split(".")[-1]

    if not ext2 in video_extensions:
        return False

    if not ext1 == ext2:
        return False

    vid1 = cv2.VideoCapture(vid1_path)
    vid2 = cv2.VideoCapture(vid2_path)

    if not vid1.isOpened() or not vid2.isOpened():
        return False

    if vid1.get(cv2.CAP_PROP_FRAME_COUNT) != vid2.get(cv2.CAP_PROP_FRAME_COUNT):
        return False

    if vid1.get(cv2.CAP_PROP_FRAME_WIDTH) != vid2.get(cv2.CAP_PROP_FRAME_WIDTH):
        return False

    if vid1.get(cv2.CAP_PROP_FRAME_HEIGHT) != vid2.get(cv2.CAP_PROP_FRAME_HEIGHT):
        return False

    while True:
        ret1, frame1 = vid1.read()
        ret2, frame2 = vid2.read()

        if not ret1 or not ret2:
            break

        if not np.array_equal(frame1, frame2):
            vid1.release()
            vid2.release()
            return False

    vid1.release()
    vid2.release()
    return True

def __find_duplicate_files(*file_paths, heavy=True):
    all_files = []

    for file_path in file_paths:
        for root, dirs, files in os.walk(file_path):
            for file in files:
                all_files.append(os.path.join(root, file))

    identical_file_groups = []

    for file1, file2 in combinations(all_files, 2):
        if __file_hashes_are_identical(file1, file2) or (
            heavy and
                (__images_are_identical(file1, file2) or
                __videos_are_identical(file1, file2))):
            
            # Check if either file is already in a group
            found_group = None
            for group in identical_file_groups:
                if file1 in group or file2 in group:
                    found_group = group
                    break
            
            if found_group:
                # Add both files to the found group
                found_group.add(file1)
                found_group.add(file2)
            else:
                # Create a new group with both files
                identical_file_groups.append({file1, file2})

    # Convert sets to tuples
    identical_files = [tuple(group) for group in identical_file_groups]

    return identical_files

def generate_report(start_path, config: ConfigParser):
    print(datetime.now(), "Generating duplicate file report ... ")
    heavy = config.get("settings", "heavy_duplicate_file_checking")
    dups = __find_duplicate_files(start_path, heavy=heavy)
    with open("duplicates.txt", "w") as fi:
        for dup in dups:
            print('"', '","'.join(dup), '"', file=fi, sep="")
    print(datetime.now(), "Done!")
    return dups

def move_older(duplicate_tuples: list, config: ConfigParser):
    print(datetime.now(), "Moving duplicate files ... ")
    dest_dir = config.get("settings", "duplicate_path")
    preferred_keyword = config.get("settings", "preferred_keyword_in_dups")
    unpreferred_keyword = config.get("settings", "unpreferred_keyword_in_dups")

    create_directories(dest_dir + "/d")
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

    print(datetime.now(), "Done!")
    return moved_files
