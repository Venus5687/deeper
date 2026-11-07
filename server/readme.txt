This is a mock server for Deezer 3.x (Android).
To get it working, follow these steps:
1. Export your song in Audacity like this:
   - Format: MP3 Files
   - Channels: Stereo
   - Sample Rate: 44100 Hz
   - Bit Rate Mode: Constant
   - Quality: 128 kbps
2. Run this command in Command Prompt in the converter's directory for each song, and keep the Command Prompt open as we'll need it for later:
   - python mp3_to_dz.py (song file path, example: C:\songs\1.mp3) (desired song ID with .mp3, for example, if the song ID is 10: 10.mp3) --id (desired song ID, for example, if the song ID is 10: 10) --iv 0x0001020304050607 --secret 6734656C35387763307A7666396E6131 --verify
3. Move all the converted MP3s in the converter's directory in the "songs" folder in the root of the server folder.
4. Open the JSON in tracks.json and /albums/1.json and adjust these values:
   - URL_REWRITING: Replace 1 in 1.mp3 with SNG_ID's value.
   - SNG_ID: Replace its value with your desired Song ID (like 1 for the first song, 2 for the second song etc.).
   - PREVIEW: Same as URL_REWRITING.
   - HREF inside of MEDIA: Same as URL_REWRITING.
   - PRODUCT_TRACK_ID: Same as SNG_ID.
   - SNG_TITLE: Replace its value with your desired Song Title (example: My Awesome Song).
   - ART_ID: Same as SNG_ID but with the Artist of the Song.
   - ART_TITLE and LOCALES inside of ARTISTS: Same as SNG_TITLE but with the Artist of the Song.
   - ART_PICTURE: Replace its value with your desired MD5 hash of the Album JPEG Image because Artist JPEG Images are going to be implemented soon (example: 098f6bcd4621d373cade4e832627b4f6, if that is the value its file name will be 098f6bcd4621d373cade4e832627b4f6.jpg).
   - ALB_ID: Same as SNG_ID but with the Album of the Song.
   - ALB_TITLE: Same as SNG_TITLE but with the Album of the Song.
   - ALB_PICTURE: Replace its value with your desired MD5 hash of the Album JPEG Image (example: 098f6bcd4621d373cade4e832627b4f6, if that is the value its file name will be 098f6bcd4621d373cade4e832627b4f6.jpg).
   - MD5_ORIGIN: Replace its value with any MD5 hash.
   - DURATION: Replace its value with the desired song's duration in seconds.
   - FILESIZE and FILESIZE_MP3_128: Replace its value with the "FILE SIZE" given by the converter, without the word "bytes".
   - GAIN: Replace its value with your desired song gain in decibels. (for example: "-7.0" for -7 decibels)
Note 1: If you edit the Album ID (ALB_ID) you must also rename /albums/1.json to /albums/(new album ID).json
Note 2: Repeat all of these steps if you want to add a new song and/or album.
5. Start the server with this command in Command Prompt in the root of the server's directory: python server.py