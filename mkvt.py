import os
import subprocess
import re
import sys
import shutil
import getpass
from pathlib import Path
import argparse
from tqdm import tqdm
import yaml
import json
from time import sleep

################################################### CONFIG ###################################################

# Directory in which the script will look for additional needed files
script_directory = Path(__file__).parent

with open(os.path.join(script_directory, "mkvt_config.yaml"), "r", encoding="utf8") as f:
    config = yaml.safe_load(f)

# Directories that will not be scanned for .mkv files
ignore_dirs = config["ignore_dirs"]

# Regex to match and ignore unwanted .mkv files like trailers, samples..
pattern_unwanted = re.compile(config["pattern_unwanted"]) if config["pattern_unwanted"] != "" else re.compile(r'^.*-trailer.mkv$|^.*-sample.mkv$')

# Subformat codecs to display in the program and append to subtitle track names
sub_codec_replacements = config["sub_codec_replacements"]

# Remove all attachments (embedded fonts, covers, nfos...) during remuxing
remove_attachments_cfg = config["remove_attachments"]

# Trim other tracks to the video length
stop_after_video_ends_cfg = config["stop_after_video_ends"]

# After remuxing, use mkvpropr on the same directory to set file title, track names, languages and flags, Default: True
run_mkvp_cfg = config["run_mkvp"]

# Track order separated by spaces, at least 1 track id must be given
pattern_input = re.compile(r'^\s*\d{1,3}(?:\s+\d{1,3})*\s*$')

# Default language codes used when filtering the track selection via "p" and then selecting "d"
if config["default_filter_langs"]:
    default_filter_langs = config["default_filter_langs"]
else:
    default_filter_langs = {
        "audio": ["ja", "jpn" ,"de", "deu", "de-DE", "ger", "en", "eng", "en-GB", "en-CA", "en-US"],
        "sub": ["de", "deu", "de-DE", "ger", "en", "eng", "en-GB", "en-CA", "en-US"]}

# User friendly version printed as the Default
default_langs_readable = f'{" ".join(default_filter_langs["audio"])}, {" ".join(default_filter_langs["sub"])}'

# Audio codes are mandatory, subtitle codes optional, regional codes like en-US are supported as well as en or eng
pattern_filter_langs = re.compile(r'^\s*\w{2,3}(?:-[\d\w]{2,4})?\s*?(?:\s\w{2,3}(?:-[\d\w]{2,4})?\s*?)*,(?:\s*\w{2,3}(?:-[\d\w]{2,4})?\s*?(?:\s\w{2,3}(?:-[\d\w]{2,4})?\s*)*)?$')

# Width of the horizontal separator bar
h_bar = "─"*100

################################################## FUNCTIONS ##################################################

def parse_arguments():
    def dir_path(path):
        if os.path.isdir(path) and path != None:
            return path
        else:
            raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")
    
    parser = argparse.ArgumentParser(description='Scan for .mkv files in subdirectories, choose a new track order and batch remux them.')
    parser.add_argument('-d', '--directory',
                        help='The directory that will be recursively scanned for .mkv files.', type=dir_path, default=".", const=".", nargs="?")
    parser.add_argument('-s', '--single_folder', action='store_true',
                        help='Only scan the current folder for .mkv files, no subdirectories.')
    parser.add_argument('--remove_attachments', action='store_true',
                        help='Remove all attachments (embedded fonts, covers, nfos...) during remuxing.')
    parser.add_argument('--stop_after_video_ends', action='store_true',
                        help='Trim other tracks to the video length.')
    parser.add_argument('--run_mkvp', action='store_true',
                        help='After remuxing, use mkvpropr on the same directory to set file title, track names, languages and flags')
    

    args: argparse.Namespace = parser.parse_args()

    return args

def mkv_tools_on_path():
    if not shutil.which("mkvmerge") or not shutil.which("mkvpropedit") and sys.platform == "win32":
        choice = input("mkvmerge or mkvpropedit executable is not on PATH, open environment variable settings in Windows to add them? (y/n): ")
        if choice == "y":
            print(f"""
    Step 1: Under 'User variables for {getpass.getuser()}' select 'Path' and either double click it or click on 'Edit...'
    Step 2: Click on 'New' and paste the path to the folder on your system that contains mkvmerge.exe and mkvpropedit.exe.
            Then confirm with "OK" twice.

            Info:
            If you do not have MKVToolNix installed yet, visit this website, download and install it:
            https://mkvtoolnix.download/downloads.html#windows
            If you chose a portable installation, you can pretty much put the folder wherever you like.
            My (non portable install) executables (as of writing) for example are located in
            C:\\Program Files\\MKVToolNix\\mkvmerge.exe
            C:\\Program Files\\MKVToolNix\\mkvpropedit.exe
            Once you have decided on where to store the portable version, add that path to PATH as described above.

            Note:
            You can also add the folder that contains this script to PATH in the same way
            if you want to call it from any folder.

    Step 3: Once that is done, re-run this script.""")
            try:
                subprocess.run(["rundll32.exe", "sysdm.cpl,EditEnvironmentVariables"])
            except subprocess.CalledProcessError:
                print(f"Error opening environment variable settings.")
                sleep(1)
            sys.exit()
        else:
            print("Exiting in 1 second")
            sleep(1)
            sys.exit()
    elif not shutil.which("mkvmerge") or not shutil.which("mkvpropedit"):
        print("mkvmerge/mkvpropedit not on PATH, add them and try again.")
        sleep(1)
        sys.exit()
    else:
        return

def mkvp_on_path():
    if not shutil.which("mkvp.py") and sys.platform == "win32":
        choice = input("mkvp is not on PATH, open environment variable settings in Windows to add them? (y/n): ")
        if choice == "y":
            print(f"""
    Step 1: Under 'User variables for {getpass.getuser()}' select 'Path' and either double click it or click on 'Edit...'
    Step 2: Click on 'New' and paste the path to the folder on your system that contains mkvp.py.
            Then confirm with "OK" twice.

            Info:
            If you do not have mkvpropr yet, visit this website and download it:
            https://github.com/AverageHoarder/mkvpropr

            Note:
            You can also add the folder that contains this script to PATH in the same way
            if you want to call it from any folder.

    Step 3: Once that is done, re-run this script.""")
            try:
                subprocess.run(["rundll32.exe", "sysdm.cpl,EditEnvironmentVariables"])
            except subprocess.CalledProcessError:
                print(f"Error opening environment variable settings.")
                sleep(1)
            sys.exit()
        else:
            print("Exiting in 1 second.")
            sleep(1)
            sys.exit()
    elif not shutil.which("mkvp.py"):
        print("mkvp not on PATH, add it and try again.")
        sleep(1)
        sys.exit()
    else:
        return shutil.which("mkvp.py")

def fetch_json(file_path):
    # Get all mkv info as JSON
    mkvmerge_command = ["mkvmerge", "-J", file_path]
    try:
        mkvmerge_json = json.loads((subprocess.check_output(mkvmerge_command)))
    except subprocess.CalledProcessError:
        print(f"Error while extracting track information for {file_path}")
    return mkvmerge_json

def track_exists(track, prop, alternative=None, fallback=False):
    # Check if the desired json element exists and return an alternative or a fallback if not
    if prop in track["properties"]:
        return track["properties"][prop]
    elif alternative and alternative in track["properties"]:
        return track["properties"][alternative]
    else:
        return fallback

def get_track_info(mkvmerge_json):
    track_info = {}
    global sub_codec_replacements

    for track in mkvmerge_json["tracks"]:
        # Type
        track_type = track["type"]
        # Codec
        track_codec = track["codec"]
        if track_codec in sub_codec_replacements:
            track_codec = sub_codec_replacements[track_codec]
        # ID
        track_id = track["id"]
        # Language, prefer newer ietf language code over legacy code
        track_lang = track_exists(track, prop="language_ietf", alternative="language", fallback="und")
        # Name
        track_name = track_exists(track, prop="track_name", fallback="empty")
        # Forced flag
        track_forced = track_exists(track, prop="forced_track")
        # Default flag
        track_default = track_exists(track, prop="default_track")
        # SDH flag
        track_sdh = track_exists(track, prop="flag_hearing_impaired")
        # Commentary flag
        track_comm = track_exists(track, prop="flag_commentary")

        video_fields = {
            "id": track_id,
            "lang": track_lang,
            "name": track_name,
            "codec": track_codec
        }
        audio_fields = {
            "id": track_id,
            "lang": track_lang,
            "name": track_name,
            "codec": track_codec,
            "default": track_default,
            "comm": track_comm
        }
        subtitle_fields = {
            "id": track_id,
            "lang": track_lang,
            "name": track_name,
            "codec": track_codec,
            "forced": track_forced,
            "default": track_default,
            "sdh": track_sdh,
            "comm": track_comm
        }
        
        # Sort track info by track type as key and a list of track dictionaries as value, which store the details as key:value pairs
        if track_type == "video" and "video" in track_info:
            track_info["video"].append(video_fields)
        elif track_type == "video":
            track_info["video"] = [video_fields]
        elif track_type == "audio" and "audio" in track_info:
            track_info["audio"].append(audio_fields)
        elif track_type == "audio":
            track_info["audio"] = [audio_fields]
        elif track_type == "subtitles" and  "subtitles" in track_info:
            track_info["subtitles"].append(subtitle_fields)
        elif track_type == "subtitles":
            track_info["subtitles"] = [subtitle_fields]
        else:
            print("Parsing json failed.")
    return track_info

def create_cat(track_info): # Create distinctive categories based on track information
    cat = ""
    for tracktype, tracks in track_info.items():
        if tracktype == "video":
            for track in tracks:
                cat += f"{track["id"]}{track["lang"]}"
        elif tracktype =="audio":
            for track in tracks:
                cat += f"{track["id"]}{track["lang"]}{track["name"]}{track["default"]}"
        elif tracktype =="subtitles":
            for track in tracks:
                cat += f"{track["id"]}{track["lang"]}{track["name"]}{track["codec"]}{track["forced"]}{track["default"]}{track["sdh"]}{track["comm"]}"
    return tuple((cat,))

# Fetch video, audio and subtitle information for mkv files and optionally sort them into categories
def process_video_files(directory, single_folder, create_categories=True):
    category_dict = {}
    mkv_files = {}
    if not single_folder:
        with tqdm(desc="Sorting mkvs into categories", unit=" files", ncols=100) as pbar:
            mkv_count = 0
            pbar.set_postfix({"mkv files": mkv_count})
            for filename in os.listdir(directory): # scan the root/base directory for .mkv files
                pbar.update(1)
                match_unwanted = re.match(pattern_unwanted, filename) # Ignore trailers, samples
                if filename.endswith(".mkv") and not match_unwanted:
                    mkv_count += 1
                    pbar.set_postfix({"mkv files": mkv_count})
                    file_path = os.path.join(directory, filename)
                    # Get detailed mkv information as JSON
                    mkvmerge_json = fetch_json(file_path)
                    # Collect only the info needed for sorting and selecting
                    track_info = get_track_info(mkvmerge_json)
                    # Store track info for later use
                    mkv_files[file_path] = track_info
                    if create_categories:
                        # Create a unique category based on track information
                        cat = create_cat(track_info)
                        # Sort file paths into groups
                        if cat in category_dict:
                            category_dict[cat].append(file_path)
                        else:
                            category_dict[cat] = [file_path]
            for root, dirs, files in os.walk(directory): # scan subfolders recursively
                dirs[:] = [d for d in dirs if d.lower() not in ignore_dirs] # ignore folders containing extras etc.
                for dir in dirs:
                    for filename in os.listdir(os.path.join(root, dir)):
                        pbar.update(1)
                        match_unwanted = re.match(pattern_unwanted, filename)
                        if filename.endswith(".mkv") and not match_unwanted:
                            mkv_count += 1
                            pbar.set_postfix({"mkv files": mkv_count})
                            file_path = os.path.join(root, dir, filename)
                            # Get detailed mkv information as JSON
                            mkvmerge_json = fetch_json(file_path)
                            # Collect only the info needed for sorting and selecting
                            track_info = get_track_info(mkvmerge_json)
                            # Store track info for later use
                            mkv_files[file_path] = track_info
                            if create_categories:
                                # Create a unique category based on track information
                                cat = create_cat(track_info)
                                # Sort file paths into groups
                                if cat in category_dict:
                                    category_dict[cat].append(file_path)
                                else:
                                    category_dict[cat] = [file_path]
    else:
        with tqdm(desc="searching", unit=" files", ncols=100) as pbar:
            mkv_count = 0
            pbar.set_postfix({"mkv files": mkv_count})
            for filename in os.listdir(directory):
                pbar.update(1)
                match_unwanted = re.match(pattern_unwanted, filename)
                if filename.endswith(".mkv") and not match_unwanted:
                    mkv_count += 1
                    pbar.set_postfix({"mkv files": mkv_count})
                    file_path = os.path.join(directory, filename)
                    # Get detailed mkv information as JSON
                    mkvmerge_json = fetch_json(file_path)
                    # Collect only the info needed for sorting and selecting
                    track_info = get_track_info(mkvmerge_json)
                    # Store track info for later use
                    mkv_files[file_path] = track_info
                    if create_categories:
                        # Create a unique category based on track information
                        cat = create_cat(track_info)
                        # Sort file paths into groups
                        if cat in category_dict:
                            category_dict[cat].append(file_path)
                        else:
                            category_dict[cat] = [file_path]
    if create_categories and category_dict == {}:
        print(f"Found no .mkv files in {directory}, exiting.")
        sys.exit(1)
    elif not create_categories:
        return mkv_files
    else:        
        return category_dict, mkv_files

def split_inputs(user_input):
    # Divide the input into video, audio and subtitle parts
    video_track = user_input.split(",")[0]
    try:
        audio_tracks = user_input.split(",")[1].split()
    except IndexError:
        audio_tracks = None
    try:
        subtitle_tracks = user_input.split(",")[2].split()
    except IndexError:
        subtitle_tracks = None
    return video_track, audio_tracks, subtitle_tracks

def print_track_info(track_info, filter_active=False, filter_langs=default_filter_langs):
    order = ["video", "audio", "subtitles"]  # Define the desired order

    for tracktype in order:
        if tracktype not in track_info:
            continue  # Skip if no tracks of this type exist
 
        tracks = track_info[tracktype]
        if tracktype == "video":
            # print("Video:")
            for track in tracks:
                id = track["id"]
                lang = track["lang"]
                name = track["name"]
                codec = track["codec"]
                print(f"{id:2} | {lang:^5} | {name[:40]:40} | {codec:20}")
            print(h_bar)
        elif tracktype =="audio":
            # print("Audio:")
            for track in tracks:
                id = track["id"]
                lang = track["lang"]
                name = track["name"]
                codec = track["codec"]
                default = "Default" if track["default"] else ""
                comm = "Commentary" if track["comm"] else ""
                if filter_active and lang not in filter_langs["audio"] and lang != "und":
                    continue
                else:
                    print(f"{id:2} | {lang:^5} | {name[:40]:40} | {codec[:6]:^6} | {" "*6} | {default:^7} | {" "*3} | {comm:^10}")
            print(h_bar)
        elif tracktype =="subtitles":
            # print("Subtitles:")
            for track in tracks:
                id = track["id"]
                lang = track["lang"]
                name = track["name"]
                codec = track["codec"]
                forced = "Forced" if track["forced"] else ""
                default = "Default" if track["default"] else ""
                sdh = "SDH" if track["sdh"] else ""
                comm = "Commentary" if track["comm"] else ""
                if filter_active and lang not in filter_langs["sub"] and lang != "und":
                    continue
                else:
                    print(f"{id:2} | {lang:^5} | {name[:40]:40} | {codec[:6]:^6} | {forced:^6} | {default:^7} | {sdh:^3} | {comm:^10}")
            print(h_bar)
    if filter_active and filter_langs == dict(default_filter_langs):
        print(f'{" "*16}DEFAULT FILTER ACTIVE, ENTER "t" TO TURN IT OFF or "p" TO EDIT IT!')
    elif filter_active:
        print(f'{" "*17}CUSTOM FILTER ACTIVE, ENTER "t" TO TURN IT OFF or "p" TO EDIT IT!')

# Get the audio, subtitle and default-track info from the user
def getInput(mkv_files, movies_in_cat, category_count, filter_active=False, filter_langs={}, last_input=""):
    # Validate inputs and requery in case of mistakes
    testmovie = movies_in_cat[0]
    track_info = mkv_files[testmovie]
    group_filecount = len(movies_in_cat)
    # Create lists of the video, audio and subtitle track IDs that exist in the file for input validation
    video_ids = [str(track["id"]) for track in track_info.get("video", [])] # video IDs are not used for validation, hence the direct string conversion
    audio_ids = [track["id"] for track in track_info.get("audio", [])]
    subtitle_ids = [track["id"] for track in track_info.get("subtitles", [])]

    while True:
        print()
        print(h_bar)
        print(os.path.basename(testmovie)[:100])
        print(h_bar)
        print_track_info(track_info=track_info, filter_active=filter_active, filter_langs=filter_langs)
        print(h_bar)
        print('Audio and subtitle track order example: 2 1 4 3 5' if not last_input else f'Last input: {last_input}. Use "i" to reuse it')
        if filter_active:
            print(f'"s" skip, "p" edit filter, "t" deactivate filter, "n" apply selection "f" filenames, "ff" filepaths')
        elif filter_langs != dict(default_filter_langs):
            print(f'"s" skip group, "p" filter by language, "t" activate custom filter, "f" filenames, "ff" filepaths')
        else:
            print(f'"s" skip group, "p" filter by language, "t" activate default filter, "f" filenames, "ff" filepaths')
        print(h_bar)
        user_input = input(f"Group {category_count + 1} contains {group_filecount} " + ("files." if group_filecount > 1 else "file.") + " \nCodes please:\n")

        # Skip the current group
        if user_input == "s":
            return user_input, filter_active, last_input
        # Filter the displayed tracks via language codes
        elif user_input == "p":
            while True:
                print(h_bar)
                user_input = input(f"""\
Enter audio and subtitle language codes to filter the selection.
Enter 'd' to use the default.
Default:
{default_langs_readable}
Codes please:\n""")
                if user_input == "d":
                    filter_active = True
                    filter_langs = dict(default_filter_langs)
                    break
                elif re.match(pattern_filter_langs, user_input):
                    filter_active = True
                    filter_langs["audio"] = user_input.split(",")[0].split()
                    filter_langs["sub"] = user_input.split(",")[1].split()
                    break
                else:
                    print("Invalid language code(s) or syntax, try again.")
                    sleep(1)
                    continue
            continue
        # Toggle the quick filter
        elif user_input == "t":
            filter_active = not filter_active
            continue
        # Add all tracks that pass the filters as inputs if you don't want to change their order, should be a quick way to only remove unwanted tracks
        elif user_input == "n" and filter_active:
            filtered_audio_ids = [track["id"] for track in track_info.get("audio", [])if track["lang"] in filter_langs["audio"]]
            filtered_subtitle_ids = [track["id"] for track in track_info.get("subtitles", [])if track["lang"] in filter_langs["sub"]]
            filtered_inputs = filtered_audio_ids + filtered_subtitle_ids
            inputs_and_ids = {"inputs": [str(tid) for tid in filtered_inputs],
                              "video_ids": video_ids,
                              "audio_ids": [str(tid) for tid in filtered_inputs if tid in audio_ids],
                              "subtitle_ids": [str(tid) for tid in filtered_inputs if tid in subtitle_ids]}
            return inputs_and_ids, filter_active, last_input
        # List the filenames of all files in the current group
        elif user_input == "f":
            print(h_bar)
            print(f"{group_filecount} " + ("files" if group_filecount > 1 else "file") + " will be affected:")
            for file_path in movies_in_cat:
                print(os.path.basename(file_path))
            print(h_bar)
            input("Press Enter to continue...")
            continue
        # List the absolute paths of all files in the current group
        elif user_input == "ff":
            print(h_bar)
            print(f"{group_filecount} " + ("files" if group_filecount > 1 else "file") + " will be affected:")
            for file_path in movies_in_cat:
                print(os.path.abspath(file_path))
            print(h_bar)
            input("Press Enter to continue...")
            continue
        # Set the user input to the last input
        elif user_input == "i":
            user_input = last_input
        match_order = re.match(pattern_input, user_input)
        if not match_order:
            print("Invalid code(s) or syntax, try again.")
            sleep(1)
            continue
        # Split the input into a list of track IDs (int)
        inputs = user_input.strip().split()
        inputs_int = [int(i) for i in inputs]
        # Check for duplicate ids in the input
        if len(set(inputs_int)) != len(inputs_int):
            print("Duplicate track ids detected, try again!")
            sleep(1)
            continue
        # Check if all inputs correspond to either an audio track ID or a subtitle track ID
        if match_order and all(num in audio_ids or num in subtitle_ids for num in inputs_int):
            inputs_and_ids = {"inputs": inputs,
                              "video_ids": video_ids,
                              "audio_ids": [str(tid) for tid in inputs_int if tid in audio_ids],
                              "subtitle_ids": [str(tid) for tid in inputs_int if tid in subtitle_ids]}
            last_input = user_input
            return inputs_and_ids, filter_active, last_input
        else:
            print("Invalid track ids, try again.")
            sleep(1)
            continue

def remux_files(category_inputs, category_dict):
    mkvs_to_remux = 0
    remuxed_files = []
    failed_files = 0
    for cat, inputs_ids in category_inputs.items():
        mkvs_to_remux += len(category_dict[cat])
    with tqdm(total = mkvs_to_remux, position=0, desc="Remuxing ", unit="mkv files", ncols=100) as pbar:
        for cat, inputs_ids in category_inputs.items():
            for mkv in category_dict[cat]:
                # Construct the output file path by adding '_new' before the extension
                output_path = mkv.replace('.mkv', '.new.mkv')

                # Convert the track order from ["1", "2", "3", "4", "5"] to 0:0,0:1,0:2 etc. First add all video tracks as those are always kept
                new_order = f'0:{inputs_ids["video_ids"][0]}'
                if len(inputs_ids["video_ids"]) > 1:
                    for video_id in inputs_ids["video_ids"][1:]:
                        new_order = f'{new_order},0:{video_id}'
                # Add the audio and video inputs to the track order
                for track_id in inputs_ids["inputs"]:
                    new_order = f'{new_order},0:{track_id}'
                
                # Construct the mkvmerge command
                mkvmerge_cmd = [
                    'mkvmerge', '-o', output_path,  # Specify output file
                    "--track-order", new_order
                ]
                
                # Remove all attachments from the files
                if remove_attachments: mkvmerge_cmd.append("-M")
                # Trim other tracks to the video length
                if stop_after_video_ends: mkvmerge_cmd.append("--stop-after-video-ends")
                # Only keep audio tracks chosen via input
                if inputs_ids["audio_ids"]: mkvmerge_cmd.extend(["--audio-tracks", ",".join(inputs_ids["audio_ids"])])
                # Only keep subtitle tracks chosen via input, if none are chosen, don't copy existing subtitles
                mkvmerge_cmd.extend(["--subtitle-tracks", ",".join(inputs_ids["subtitle_ids"])]) if inputs_ids["subtitle_ids"] else mkvmerge_cmd.append("--no-subtitles")
                # Input mkv file
                mkvmerge_cmd.append(mkv)
                try:
                    subprocess.run(mkvmerge_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                    remuxed_files.append(mkv)
                    pbar.update(1)
                except subprocess.CalledProcessError:
                    print(f"Error while remuxing to {output_path}. Deleting failed output file.")
                    failed_files += 1
                    try:
                        os.remove(output_path)
                    except OSError:
                        pass
    return remuxed_files, failed_files

def replace_original_files(remuxed_files):
    with tqdm(total = len(remuxed_files), desc="Replacing ", unit="files", ncols=100) as pbar:
        for mkv_path in remuxed_files:
            output_path = mkv_path.replace('.mkv', '.new.mkv')
            try:
                if os.path.isfile(output_path):
                    os.remove(mkv_path)
                    os.rename(output_path, mkv_path)
                    pbar.update(1)
            except OSError:
                print(f"Could not replace {mkv_path}.")
                pass

def clean_up(remuxed_files):
    with tqdm(total = len(remuxed_files), desc="Cleaning up ", unit="files", ncols=100) as pbar:
        for mkv_path in remuxed_files:
            output_path = mkv_path.replace('.mkv', '.new.mkv')
            try:
                if os.path.isfile(output_path):
                    os.remove(output_path)
                    pbar.update(1)
            except OSError:
                print(f"Could not remove {output_path}.")
                pass
        print("Cleanup done, exiting in 1 second.")
        sleep(1)
        sys.exit()

def main(args):
    args = parse_arguments()
    directory = args.directory
    single_folder = args.single_folder
    global remove_attachments
    remove_attachments = True if args.remove_attachments or remove_attachments_cfg else False
    global stop_after_video_ends
    stop_after_video_ends = True if args.stop_after_video_ends or stop_after_video_ends_cfg else False
    run_mkvp = True if args.run_mkvp or run_mkvp_cfg else False

    # Check if the required external programs are available on PATH and abort if not
    mkv_tools_on_path()

    category_dict, mkv_files = process_video_files(directory=directory, single_folder=single_folder, create_categories=True)
    categories = list(category_dict.keys()) # Create a list of categories
    filter_active = False
    filter_langs = dict(default_filter_langs)
    # Dictionary that has a category as it's key and the inputs as the value
    category_inputs = {}

    with tqdm(total = len(categories), position=0, desc="Collecting category inputs", unit="cat", ncols=100) as pbar:
        category_count = 0
        last_input = ""
        for cat in categories:
            movies_in_cat = [movie for movie in category_dict[cat]]
            # Query user for track ids for reordering
            inputs_and_ids, filter_active, last_input = getInput(mkv_files=mkv_files, 
                                                 movies_in_cat=movies_in_cat,
                                                 category_count=category_count,
                                                 filter_active=filter_active,
                                                 filter_langs=filter_langs,
                                                 last_input=last_input)
            if inputs_and_ids == "s":
                print("Skipping current category.")
                pbar.update(1)
                category_count += 1
                continue
            else:
                category_inputs[cat]=inputs_and_ids
            pbar.update(1)
            category_count += 1

    if not category_inputs:
        print("No changes needed, exiting in 1 second.")
        sleep(1)
        sys.exit()

    # Remux all selected mkv files in one go
    remuxed_files, failed_files = remux_files(category_inputs=category_inputs, category_dict=category_dict)
    
    if remuxed_files:
        user_input = input("Replace original .mkv files with the remuxed .new.mkv ones?\nTHIS STEP IS DESTRUCTIVE! CHECK THE RESULTS BEFORE YOU CONTINUE!\n(y/n): ")
        if user_input == "y":
            # Replace the original files with the .new.mkv versions
            replace_original_files(remuxed_files=remuxed_files)
            if run_mkvp:
                mkvp_path = mkvp_on_path()
                mkvp_cmd = ["python", mkvp_path, "-d", directory]
                if single_folder:
                    mkvp_cmd.append("-s")
                try:
                    subprocess.run(mkvp_cmd)
                except subprocess.CalledProcessError:
                    print(f"Error while executing mkvpropr.")

        elif user_input == "n":
            user_input = input("Remove the leftover .new.mkv files?\n(y/n): ")
            if user_input == "y":
                clean_up(remuxed_files)
            else:
                print("Execution aborted. Exiting in 1 second.")
                sleep(1)
                sys.exit()

    exit_time = 1
    print(f"Remuxed {len(remuxed_files)} mkv " + ("file ." if len(remuxed_files) == 1 else "files. ") +
          f"{failed_files} " + ("error. " if failed_files == 1 else "errors. ") + 
          f"Exiting in {exit_time} " + ("second." if exit_time == 1 else "seconds."))
    sleep(exit_time)
    sys.exit(0)

if __name__ == "__main__":
    args = parse_arguments()
    try:
        main(args)
    except KeyboardInterrupt:
        print("Interrupted, exiting.")
        try:
            sys.exit(130)
        except SystemExit:
            os._exit(130)