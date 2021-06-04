# python-yt_downloader

A for self-use and python-based YouTube downloader application with a simple GUI.

Stand-alone application executable (main.exe) can be found in ~/dist directory.

Please download ffmpeg first and set it as a PATH environment variable before using the application.
See: https://www.wikihow.com/Install-FFmpeg-on-Windows

To run the Python file instead, please install requirements first by executing `pip install -r requirements.txt`.

Some things to know:

- this app will not overwrite existing files EXCEPT for any file named temp_video and temp_audio

- downloaded videos/audio will always be in mp4 format

- if invalid chars in the video's title are detected, they are replaced with an underscore or single quotation marks

- ~~GUI may freeze while fetching the YouTube video or when compiling~~ (fixed with multithreading)

- if an error occurs, you can see more details at the console

- if a video resolution is not available for download, it will automatically download highest resolution available