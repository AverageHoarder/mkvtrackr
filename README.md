# mkvtrackr
## Python script to interactively and recursively filter and reorder tracks of mkv files in groups based on track combinations and properties

As a perfectionist hoarder who wants the track order to be consistent between all my files, writing this script was inevitable.<br>
I used to manually reorder tracks and then remux mkv files in MKVToolNix, which (especially for tv shows) is inefficient, prone to errors and slow.<br>
A step up from that was performing changes in MKVToolNix on one file, copying the resulting options and using these on a batch of other files with the same tracks.<br>
However, manually grouping files by identical track properties and then performing changes once per group in MKVToolNix was still tedious and annoying work.<br>
The next step was writing .bat files that used mkvmerge to change the track order, but that also quickly became unwieldy.<br>
  
The conclusion to these problems is what this script does. It recursively searches all .mkv files in all subfolders (except for excluded ones), groups them based on their video, audio and subtitle track combinations, track names and flags and then lets the user decide once per group which audio and subtitle tracks should be kept in which order. Once the user has decided on options for all groups, all the files are remuxed via mkvmerge in one go.<br>
This script used to be 2 scripts. The first one allowed to quickly remove all audio and subtitle tracks that didn't match selected language codes (for files with many tracks).<br>
The second script allowed to change the order of the remaining tracks. This was inefficient as it meant remuxing each file twice to filter and reorder the tracks.<br>
In this script the tracks can be filtered during the selection, so the files are only rewritten once.<br>

It has many convenience features I've added over the last 1,5 years and I've used it on thousands of movies and episodes, but more on that below.<br>

mkvtrackr works best in conjunction with [mkvpropr](https://github.com/AverageHoarder/mkvpropr) and per default calls mkvpropr after remuxing all files to efficiently set file title, track names, languages and flags (which doesn't require remuxing).

## How to install mkvtrackr

### Prerequisites

**Required:**
1. [python](https://www.python.org/downloads/) must be installed (tested with python 3.12.3)
2. [tqdm](https://github.com/tqdm/tqdm) must be installed, I used `pip3 install tqdm`
3. [MKVToolNix](https://mkvtoolnix.download/) must be installed and on PATH

If mkvmerge or mkvpropedit are not on PATH, the script will complain and (if on Windows) open the environment variables settings with instructions on how to add them to PATH.

### Downloading the script

You can download/clone the entire repository and extract "mkvt.py" and "mkvt_config.yaml".<br>
If you want to be able to call it from anywhere on your system (which is more convenient than supplying a path via `-d`), you can add the folder containing "mkvt.py" to your PATH.

## Usage

### Output from -h:

```
usage: mkvt.py [-h] [-d [DIRECTORY]] [-s] [--remove_attachments] [--stop_after_video_ends] [--run_mkvp]

Scan for .mkv files in subdirectories, choose a new track order and batch remux them.

options:
  -h, --help            show this help message and exit
  -d [DIRECTORY], --directory [DIRECTORY]
                        The directory that will be recursively scanned for .mkv files.
  -s, --single_folder   Only scan the current folder for .mkv files, no subdirectories.
  --remove_attachments  Remove all attachments (embedded fonts, covers, nfos...) during remuxing.
  --stop_after_video_ends
                        Trim other tracks to the video length.
  --run_mkvp            After remuxing, use mkvpropr on the same directory to set file title, track
                        names, languages and flags
```

## Configuring mkvtrackr
### Before running the script for the first time, it's recommended to customize it by editing "mkvt_config.yaml" to adjust it for your collection

### default_filter_langs
This defines the default filter that you can set when using "p" followed by "d" as inputs. Tracks with language codes on this list will remain in the selection. All other tracks are hidden while the filter is active to make the selection of a new track order easier for files with many tracks.<br>
Make sure you include all variations of the language codes that are present in your collection.<br>
For German for example: `de, deu, de-DE, ger` are all valid language codes.<br>

### ignore_dirs
The script won't recurse into folders that match entries of this list. I've added standard extras folders.<br>
You can still run the script in a folder on this list if you call it in the folder itself or pass the folder name via `-d`.

### sub_codec_replacements
Here you can set what you'd like displayed in the track order selection as the sub format. Usually there's no need to change this.

### pattern_unwanted
With this regex you can exclude files you don't want to edit. Trailers, sample files, proof files and so on.

### remove_attachments
Remove all attachments (embedded fonts, covers, nfos...) during remuxing. Disabled by default.

### stop_after_video_ends
Trim other tracks to the video length. Disabled by default.

### run_mkvp
After remuxing, use mkvpropr on the same directory to set file title, track names, languages and flags. Enabled by default.

## Usage in detail
Either run `mkvt.py` in the root of the directory you wish to recursively edit or provide the directory via `mkvt.py -d`<br>
After scanning, extracting information and grouping the files, the script will ask you for inputs for each group of files.<br>
You can then either skip the group, filter the tracks with your default filter, set a new filter or simply enter a new track order.

**Example movie**:<br>
id tracktype name<br>
0 video Mononoke Hime<br>
1 audio english<br>
2 audio german<br>
3 audio japanese<br>
4 subtitle dutch<br>
5 subtitle english<br>
6 subtitle japanese<br>
7 subtitle german<br>
  
By entering:<br>
`3 2 1 7 5`<br>
as the input, the movie would be remuxed to:<br>
  
id tracktype name<br>
0 video Mononoke Hime<br>
1 audio japanese<br>
2 audio german<br>
3 audio english<br>
4 subtitle german<br>
5 subtitle english<br>
  
Deleting the dutch and japanese subtitles and changing the order of the other tracks. The video track id must not be specified as video tracks are always kept.

## Special inputs
While the script is running and prompts the user for input, a few special options/inputs are available.

**s to skip**<br>
Only use `s` as input to skip the current group.

**p to set and enable a track language filter**<br>
Only use `p` as input to set a language filter for the track selection. You can enter language codes for audio and subtitle tracks, separated by a `,`.<br>
Alternatively, you can enter `d` to set the default filter defined in the config file.<br>
Entering `ja de en, de en` for example would only show tracks matching these language codes in the track order selection.

**t to toggle the filter**<br>
Only use `t` as input to enable or disable the current filter. If no custom filter has been set, the default filter is used.

**n to apply the current filter (only applies when a filter is active)**<br>
Only use `n` as input to use the currently visible tracks and their order as the final order. This is a quick way to process files where the tracks that you want to keep are in the correct order but there are some tracks in other languages that you want to remove. By setting a filter that only retains the tracks you want and using `n` as the input, all other tracks are removed without requiring the user to type the track order.

**f to show filenames**<br>
Only use `f` as input to show the filenames of each file in the group (this can help you make sure that you are only editing files that you want to edit).

**ff to show absolute filepaths**<br>
Only use `ff` as input to show the absolute paths of each file in the group.