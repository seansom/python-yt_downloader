from pytube import YouTube, Playlist
from hurry.filesize import size
from pathlib import Path
from PyQt5 import QtWidgets as qtw
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSlot
import sys, os, re, ffmpeg, pytube, urllib, traceback


try:
    from yt_downloader_gui.mainwindow import Ui_MainWindow
except:
    sys.exit('Please run gui builder first.')


class yt_downloader():

    def __init__(self, url, isplaylist= False, progress_callback= None, complete_callback= None):
        
        self.url = url
        self.isplaylist = isplaylist
        self.progress_callback = progress_callback
        self.complete_callback = complete_callback

        self.res_options = []
        self.filesize_options = []
        self.stream_dict = {}

        self.vid = None


            
    def prepare_vid(self):

        """Function that retrieves the YouTube stream/s for download.
        """        

        if self.vid is not None:
            return

        if self.isplaylist:
            self.vid = []
            playlist = Playlist(self.url)
            playlist._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")

            playlist_len = len(playlist)

            for i in range(playlist_len):
                self.vid.append(yt_downloader(playlist[i], progress_callback=self.progress_callback, complete_callback=self.complete_callback))

        else:
            print(f'Initializing video for download:    {self.url}')
            self.vid = YouTube(self.url, on_progress_callback=self.progress_callback, on_complete_callback=self.complete_callback)


            
    def get_res_options(self):

        """Shows which resolutions are available to download.
        If a playlist, shows resolutions which are common to all videos in the playlist.

        Returns:
            list of strings
            i.e. ['144p', '240p', '360p']
        """        
        self.prepare_vid()

        if self.res_options:
            return self.res_options

        if not self.isplaylist:

            for i in self.vid.streams.filter(adaptive=True, file_extension='mp4', type='video'):
                if i.resolution is not None:
                    self.stream_dict[i.resolution] = i

            self.res_options = sorted(list(self.stream_dict.keys()), key=(lambda x: int(x[:-1])))
            self.res_options.append('audio')

            self.stream_dict['audio'] = self.vid.streams.filter(file_extension='mp4', type='audio')[-1]


        elif self.isplaylist:

            res_options_li = []
            for i in self.vid:
                i.get_res_options()
                res_options_li.append(i.res_options)


            for i in res_options_li[0]:
                iscommon = True

                for j in res_options_li:
                    if i not in j:
                        iscommon = False
                        break

                if iscommon:
                    self.res_options.append(i)

        return self.res_options



    def get_filesize_options(self):

        """Shows the filesizes are with respect to the order found in self.res_options.
        If a playlist, shows total filesizes given all videos are downloaded with the same resolution.

        Returns:
            [type]: [description]
        """                
        
        if self.filesize_options:
            return self.filesize_options

        if not self.isplaylist:
            for res in self.get_res_options():
                
                audio_file_size = self.stream_dict['audio'].filesize

                if res != 'audio':
                    self.filesize_options.append(size(self.stream_dict[res].filesize + audio_file_size) + 'B')
                
                else:
                    self.filesize_options.append(size(audio_file_size) + 'B')


        elif self.isplaylist:

            for i in self.get_res_options():

                filesize_sum = 0

                for j in self.vid:

                    if i != 'audio':
                        filesize_sum += (j.stream_dict[i].filesize + j.stream_dict['audio'].filesize)
                    else:
                        filesize_sum += j.stream_dict[i].filesize

                self.filesize_options.append(size(filesize_sum) + 'B')


        return self.filesize_options


    
    def download(self, res, dirname=None, finished_callback=None):

        """Function that downloads the video at the res specified and inside an optional directory.
        If playlist, this function will recursively download all videos in the playlist, all with the same resolution.
        """        

        self.prepare_vid()

        if dirname:
            filepath = os.path.join(Path.home(), 'Downloads', dirname)
            
            if os.path.exists(filepath):
                os.chdir(filepath)

            else:
                os.chdir(os.path.join(Path.home(), 'Downloads'))
                os.mkdir(dirname)
                os.chdir(filepath)
            
        elif dirname is None:
            filepath = os.path.join(Path.home(), 'Downloads')
            os.chdir(filepath)



        if not self.isplaylist:
            filename = self.vid.title

            try:
                filename = re.sub(r'[\\\/\:\*\?\<\>\|]', '_', filename)
                filename = re.sub(r'[\"]', '\'', filename)
            except:
                pass

            try:
                os.remove('temp_video.mp4')
                os.remove('temp_audio.mp4')
            except:
                pass


            if os.path.isfile(f'{filename}.mp4'):
                self.complete_callback(None, os.path.join(filepath, f'{filename}.mp4'))
                return


            if not self.stream_dict:
                if res != 'audio':
                    self.stream_dict[res] = self.vid.streams.filter(resolution=res, adaptive=True, file_extension='mp4', type='video').first()
                
                    # download the highest available resolution if specified res is not available
                    if self.stream_dict[res] is None:
                        self.stream_dict[res] = self.vid.streams.filter(adaptive=True, file_extension='mp4', type='video').order_by('resolution').desc().first()

                self.stream_dict['audio'] = self.vid.streams.filter(file_extension='mp4', type='audio')[-1]
   

            if res != 'audio':
                

                self.stream_dict[res].download(filename='temp_video')
                self.stream_dict['audio'].download(filename='temp_audio')


                video_stream = ffmpeg.input('temp_video.mp4')
                audio_stream = ffmpeg.input('temp_audio.mp4')

                ffmpeg.output(audio_stream, video_stream, f'{filename}.mp4').run()

                os.remove('temp_video.mp4')
                os.remove('temp_audio.mp4')


            elif res == 'audio':
                self.stream_dict['audio'].download(filename=f'{filename}')


        elif self.isplaylist:
            for i in self.vid:
                i.download(res, dirname)




class Worker(QRunnable):

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs



    @pyqtSlot()
    def run(self):
        try:
            self.fn(*self.args, **self.kwargs)
          
        except Exception as e:
            error_name = type(e).__name__

            print(f'=============================\n{error_name} OCCURED.\n=============================')
            traceback.print_exc()
            print(f'=============================\n{error_name} OCCURED.\n=============================')

            # other common errors: pytube.exceptions.RegexMatchError, urllib.error.URLError

            if error_name == 'ConnectionResetError':
                self.kwargs['finished_callback']('Connnection Reset')

            elif error_name == 'ConnectionError':
                self.kwargs['finished_callback']('Connnection Error')

            elif error_name == 'FileNotFoundError':
                self.kwargs['finished_callback']('ffmpeg Not Installed')

            elif error_name == 'URLError':
                self.kwargs['finished_callback']('No Internet')

            else:
                self.kwargs['finished_callback'](error_name)

            return
        
        self.kwargs['finished_callback']()

            

class MainWindow(qtw.QMainWindow):

    def __init__(self, app, parent= None):
        super().__init__(parent)

        self.app = app

        # setup multithreading
        self.threadpool = QThreadPool()
        print(f"Multithreading with maximum {self.threadpool.maxThreadCount()} threads")

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.setWindowTitle("Som's YT Downloader")

        self.setFixedSize(394, 275)

        self.warninglist = ['Invalid URL']
        self.update_dl_ready()

        
        self.ui.custom_dir_name_check.toggled.connect(lambda state: self.custom_dir_name_enabled(state))
        self.ui.custom_dir_name_box.textChanged.connect(lambda: self.isValid_custom_dir_name(self.ui.custom_dir_name_box.text()))
        self.ui.url_box.editingFinished.connect(lambda: self.isValid_url(self.ui.url_box.text()))
        self.ui.download_button.clicked.connect(self.dl_start)



    def update_dl_ready(self):
        
        if not self.warninglist:
            self.ui.status_text.setText('None')
            self.ui.download_button.setEnabled(True)
        
        else:
            self.ui.status_text.setText(', '.join(self.warninglist))
            self.ui.download_button.setEnabled(False)



    def custom_dir_name_enabled(self, state):

        self.ui.custom_dir_name_box.setEnabled(state)

        if state:
            self.warninglist.append('Invalid Dir Name')

        elif not state:
            self.ui.custom_dir_name_box.setText('')

            if 'Invalid Dir Name' in self.warninglist:
                self.warninglist.remove('Invalid Dir Name')

        self.update_dl_ready()
            


    def isValid_custom_dir_name(self, dirname):

        """Function that determines if user-inputted dir name is valid for Windows.
        """                

        if re.search(r'[\\\/\:\*\?\<\>\|\"]', dirname) or not self.ui.custom_dir_name_box.text():

            if 'Invalid Dir Name' not in self.warninglist:
                self.warninglist.append('Invalid Dir Name')

            self.ui.custom_dir_name_box.setText('')

        elif 'Invalid Dir Name' in self.warninglist:
            self.warninglist.remove('Invalid Dir Name')
        
        self.update_dl_ready()



    def isValid_url(self, url):

        """Function that determines if user-inputted url is a valid YouTube video url.
        """        

        if re.search(r'https://www\.youtube\.com/.+', url):
            if 'Invalid URL' in self.warninglist:
                self.warninglist.remove('Invalid URL')
        
        else:
            if 'Invalid URL' not in self.warninglist:
                self.warninglist.append('Invalid URL')

            self.ui.url_box.setText('')

        self.update_dl_ready()



    def dl_start(self):

        """Disables UI and starts the download using multithreading.
        """        

        self.ui.curr_download_text.setText('Processing Download')

        url = self.ui.url_box.text()
        isplaylist = self.ui.is_playlist_check.checkState()
        res = self.ui.download_setting_option.currentText()
        dirname = self.ui.custom_dir_name_box.text()

        self.ui.url_box.setEnabled(False)
        self.ui.is_playlist_check.setEnabled(False)
        self.ui.custom_dir_name_check.setEnabled(False)
        self.ui.custom_dir_name_box.setEnabled(False)
        self.ui.download_setting_option.setEnabled(False)
        self.ui.download_button.setEnabled(False)

        for_download = yt_downloader(url, isplaylist=isplaylist, progress_callback=self.show_progress, complete_callback=self.show_complete)
        
        if dirname:
            worker = Worker(for_download.download, res, dirname=dirname, finished_callback=self.show_finished)
        else:
            worker = Worker(for_download.download, res, finished_callback=self.show_finished)

        self.threadpool.start(worker)



    def show_progress(self, stream, chunk, bytes_remaining):

        """Callback function to show download progress.
        """        

        progress = round((((stream.filesize - bytes_remaining) / stream.filesize) * 100), 2)
        
        if stream.type == 'video':
            print(f'Downloading [video]: {stream.title} || {progress}')
            title = f'[video] {stream.title}'
        else:
            print(f'Downloading [audio]: {stream.title} || {progress}')
            if progress < 99:
                title = f'[audio] {stream.title}'
            else:
                title = f'[compiling] {stream.title}'

            
        self.ui.progress_text.setText(f'{progress} %')

        if len(title) > 30:
            title = title[:29] + '...'

        self.ui.curr_download_text.setText(title)



    def show_complete(self, stream, filepath):

        """Callback function to show download of a single video is completed.
        """        

        if self.ui.progress_text.text() != '100.0 %':
            self.ui.progress_text.setText('100.0 %')

        print('=============================')
        print(f'Downloaded Path: {filepath}')
        print('=============================')



    def show_finished(self, error_name= None):

        """Callback function to show that the full download of a single video or playlist is completed.
        """        

        if error_name is None:
            self.ui.curr_download_text.setText('Download Complete')

        elif error_name == 'Connection Reset':
            self.ui.curr_download_text.setText('Connection Reset. Restarting...')
            self.dl_start()
            return

        else:
            if len(error_name) > 30:
                error_name = error_name[:29] + '...'
            self.ui.curr_download_text.setText(error_name)

        self.ui.url_box.setText('')
        self.isValid_url('')

        self.ui.custom_dir_name_check.setCheckState(False)
        self.ui.is_playlist_check.setCheckState(False)


        self.ui.url_box.setEnabled(True)
        self.ui.is_playlist_check.setEnabled(True)
        self.ui.custom_dir_name_check.setEnabled(True)
        self.ui.download_setting_option.setEnabled(True)
        self.ui.download_button.setEnabled(True)


        self.update_dl_ready()



def main():
    print("Loading UI. Please wait.")

    os.chdir(os.path.dirname(sys.argv[0]))

    app = qtw.QApplication(sys.argv)
    window = MainWindow(app)

    window.show()
    sys.exit(app.exec_())



if __name__ == "__main__":
    main()
