#!/usr/bin/python2

#
# Simple file to keep your iPod/iPhone in sync with a directory on your
# hard drive. It's a bit inefficient because it rebuilds the database each time, but it's 5x faster than using any of
# the Linux/iPod syncing tools because it uses gvfs-copy instead of fuse.
#
# ISSUES:
# - Does not copy artwork (yet)
# - Only tested with iOS 4.3.3 (with DBVersion changed from 5->4)
#
# NOTE: You may need to change python2 to python above to work on your system
#


import os, subprocess
import unicodedata
import gpod
from beets.mediafile import MediaFile

###################################
###     EDIT THESE VARIABLES    ###
###################################

music_dir = ""   # The local directory you want to keep in sync with your ipod
mp = ""          # The mount point on your ipod. Can be something like "/mnt/ipod" or "/home/user/.gvfs/User%27s iPod"
uuid = ""        # UUID of your ipod. Run ideviceinfo to get it. Used to transfer files with gvfs-copy


###################################
### DO NOT EDIT BELOW THIS LINE ###
###################################

music_formats = ['mp3']
ipod_path_prefix = 'iTunes_Control/Music'
ipod_music_dir = os.path.join(mp, ipod_path_prefix)

# Necessary on linux since filenames are just stored as bytestrings. This assumes the filenames contain utf-8 characters only
def exists_on_disk(file):
    if os.path.isfile(file):
        return True
    else:
        unicode_file = file.decode('utf-8')
        normalized_file = unicodedata.normalize("NFC", unicode_file)
        decompressed_file = normalized_file.encode('utf-8')
		
        if os.path.isfile(decompressed_file):
            return True
        else:
            return False
	
for r,d,f in os.walk(ipod_music_dir):
    for files in f:
        if any(files.endswith(x) for x in music_formats):
            full_ipod_filepath = os.path.join(r, files)
            relative_filepath = full_ipod_filepath[len(ipod_music_dir)+1:] # This gives us 'Artist/Album/Song.mp3'
            full_local_filepath = os.path.join(music_dir, relative_filepath)
            if not exists_on_disk(full_local_filepath):
                print "Deleting from iPod: " + relative_filepath
                os.remove(full_ipod_filepath)
			
for r,d,f in os.walk(music_dir):
    for files in f:
        if any(files.endswith(x) for x in music_formats):
            full_local_filepath = os.path.join(r, files)
            relative_filepath = full_local_filepath[len(music_dir)+1:] # This gives us 'Artist/Album/Song.mp3'
            full_ipod_filepath = os.path.join(ipod_music_dir, relative_filepath)
            if not os.path.isfile(full_ipod_filepath):
                dir_name = os.path.dirname(full_ipod_filepath)
                if not os.path.exists(dir_name):
                    os.makedirs(dir_name)
                if "#" in full_local_filepath:
                    os.rename(full_local_filepath, full_local_filepath.replace("#","_"))
                    full_local_filepath = full_local_filepath.replace("#","_")
                    relative_filepath = relative_filepath.replace("#","_")
                print "Copying: " + relative_filepath
                subprocess.call(["gvfs-copy", full_local_filepath, "afc://" + uuid + "/" + ipod_path_prefix + "/" + relative_filepath])
            else:
                if os.path.getsize(full_local_filepath) != os.path.getsize(full_ipod_filepath):
                    if "#" in full_local_filepath:
                        os.rename(full_local_filepath, full_local_filepath.replace("#","_"))
                        full_local_filepath = full_local_filepath.replace("#","_")
                        relative_filepath = relative_filepath.replace("#","_")
                    print "Updating: " + relative_filepath
                    subprocess.call(["gvfs-copy", full_local_filepath, "afc://" + uuid + "/" + ipod_path_prefix + "/" + relative_filepath])
					
### Done syncing the music directory with the ipod. Now let's rebuild the database with
### the new changes.

db = gpod.itdb_parse(mp, None)

### First delete everything from ipod database
tracks = gpod.sw_get_tracks(db)
for track in tracks:
	
    # Remove it from any playlists it might be on
    for pl in gpod.sw_get_playlists(db):
        if gpod.itdb_playlist_contains_track(pl, track):
            gpod.itdb_playlist_remove_track(pl, track)
    
    # Remove it from the master playlist
    gpod.itdb_playlist_remove_track(gpod.itdb_playlist_mpl(db), track)
    
    # Remove it from the database
    gpod.itdb_track_remove(track)
    
### Now lets add everything from our music directory, deleting any files that don't exist locally

songs = []

for r,d,f in os.walk(ipod_music_dir):
    for files in f:
        if any(files.endswith(x) for x in music_formats):
            songs.append(os.path.join(r, files))
            
for song in songs:
    
    try:
        f = MediaFile(song)
    except:
        print "Error reading '" + song + "'"
        continue

    track = gpod.itdb_track_new()
    track.title = f.title.encode('utf-8')
    track.ipod_path = song[len(mp):].replace('/',':')
    track.album = f.album.encode('utf-8')
    track.artist = f.artist.encode('utf-8')
    track.albumartist = f.albumartist.encode('utf-8')
    track.genre = f.genre.encode('utf-8')
    track.filetype = song.split('.')[-1]
    track.comment = f.comments.encode('utf-8')
    track.composer = f.composer.encode('utf-8')
    track.grouping = f.grouping.encode('utf-8')

    track.sort_artist = f.artist_sort.encode('utf-8')
    track.sort_albumartist = f.albumartist_sort.encode('utf-8')
	
    #track.size = f.size
    track.tracklen = f.length * 1000

    if f.disc:
        track.cd_nr = f.disc
    if f.disctotal:
        track.cds = f.disctotal
    if f.track:
        track.track_nr = f.track
    if f.tracktotal:
        track.tracks = f.tracktotal
		
    track.bitrate = f.bitrate
    track.year = f.year
	
    track.visible = 1

    gpod.itdb_track_add(db, track, -1)
    gpod.itdb_playlist_add_track(gpod.itdb_playlist_mpl(db), track, -1)
    
# Write the database
gpod.itdb_write(db, None)
