import sys, os
from PyQt5 import uic

os.chdir(os.path.dirname(sys.argv[0]))
uic.compileUiDir('yt_downloader_gui')