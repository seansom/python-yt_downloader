from pytube import YouTube, Playlist
from hurry.filesize import size
from pathlib import Path
from PyQt5 import QtWidgets as qtw
import sys, os, re, ffmpeg, pytube, urllib, traceback


# pyinstaller cannot see second-level imports

try:
    from yt_downloader_gui.mainwindow import Ui_MainWindow
except:
    sys.exit('Please run gui builder first.')


class yt_downloader():

    def __init__(self, url, isplaylist= False, callback=None):

        self.isplaylist = isplaylist
        self.res_options = []
        self.filesize_options = []
        self.stream_dict = {}


        if self.isplaylist:
            self.sub = []

            playlist = Playlist(url)
            playlist._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")

            playlist_len = len(playlist)

            for i in range(playlist_len):
                print(f'Initializing video {i + 1} of {playlist_len}    ||    {playlist[i]}')
                self.sub.append(yt_downloader(playlist[i], callback=callback))

        else:
            self.yt = YouTube(url, on_progress_callback=callback, on_complete_callback=self.download_complete)
            

            
    def get_res_options(self):

        """Shows which resolutions are available to download.
        If a playlist, shows resolutions which are common to all videos in the playlist.

        Returns:
            list of strings
            i.e. ['144p', '240p', '360p']
        """        

        if self.res_options:
            return self.res_options

        if not self.isplaylist:

            for i in self.yt.streams.filter(adaptive=True, file_extension='mp4', type='video'):
                if i.resolution is not None:
                    self.stream_dict[i.resolution] = i

            self.res_options = sorted(list(self.stream_dict.keys()), key=(lambda x: int(x[:-1])))
            self.res_options.append('audio')

            self.stream_dict['audio'] = self.yt.streams.filter(file_extension='mp4', type='audio')[-1]


        elif self.isplaylist:

            res_options_li = []
            for i in self.sub:
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
            for res in self.res_options:
                
                audio_file_size = self.stream_dict['audio'].filesize

                if res != 'audio':
                    self.filesize_options.append(size(self.stream_dict[res].filesize + audio_file_size) + 'B')
                
                else:
                    self.filesize_options.append(size(audio_file_size) + 'B')


        elif self.isplaylist:

            for i in self.get_res_options():

                filesize_sum = 0

                for j in self.sub:

                    if i != 'audio':
                        filesize_sum += (j.stream_dict[i].filesize + j.stream_dict['audio'].filesize)
                    else:
                        filesize_sum += j.stream_dict[i].filesize

                self.filesize_options.append(size(filesize_sum) + 'B')


        return self.filesize_options


    
    def download(self, res, dirname=None):

        """Function that downloads the video at the res specified and inside an optional directory.
        If playlist, this function will recursively download all videos in the playlist, all with the same resolution.
        """        

        if dirname:
            file_path = os.path.join(Path.home(), 'Downloads', dirname)
            
            if os.path.exists(file_path):
                os.chdir(file_path)

            else:
                os.chdir(os.path.join(Path.home(), 'Downloads'))
                os.mkdir(dirname)
                os.chdir(file_path)
            
        elif dirname is None:
            os.chdir(os.path.join(Path.home(), 'Downloads'))



        if not self.isplaylist:
            filename = self.yt.title

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
                return


            if not self.stream_dict:
                if res != 'audio':
                    self.stream_dict[res] = self.yt.streams.filter(resolution=res, adaptive=True, file_extension='mp4', type='video').first()
                
                    # download the highest available resolution if specified res is not available
                    if self.stream_dict[res] is None:
                        self.stream_dict[res] = self.yt.streams.filter(adaptive=True, file_extension='mp4', type='video').order_by('resolution').desc().first()

                self.stream_dict['audio'] = self.yt.streams.filter(file_extension='mp4', type='audio')[-1]
   

            if res != 'audio':
                

                self.stream_dict[res].download(filename='temp_video')
                self.stream_dict['audio'].download(filename='temp_audio')

                print(os.getcwd())

                video_stream = ffmpeg.input('temp_video.mp4')
                audio_stream = ffmpeg.input('temp_audio.mp4')

                ffmpeg.output(audio_stream, video_stream, f'{filename}.mp4').run()

                os.remove('temp_video.mp4')
                os.remove('temp_audio.mp4')


            elif res == 'audio':
                self.stream_dict['audio'].download(filename=f'{filename}')


        elif self.isplaylist:
            for i in self.sub:
                i.download(res, dirname)

    

    def download_complete(self, stream, file_path):
        print('=============================')
        print(f'Downloaded Path: {file_path}')
        print('=============================')






class MainWindow(qtw.QMainWindow):
    def __init__(self, app, parent= None):
        super().__init__(parent)

        self.app = app

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.setWindowTitle("Som's YT Downloader")

        self.setFixedSize(394, 275)

        self.warninglist = ['Invalid URL']
        self.update_dl_ready()

        
        self.ui.custom_dir_name_check.toggled.connect(lambda state: self.custom_dir_name_enabled(state))
        self.ui.custom_dir_name_box.textChanged.connect(lambda: self.isValid_customd_dir_name(self.ui.custom_dir_name_box.text()))
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

            

    def isValid_customd_dir_name(self, dirname):        

        if re.search(r'[\\\/\:\*\?\<\>\|\"]', dirname) or not self.ui.custom_dir_name_box.text():

            if 'Invalid Dir Name' not in self.warninglist:
                self.warninglist.append('Invalid Dir Name')

            self.ui.custom_dir_name_box.setText('')

        elif 'Invalid Dir Name' in self.warninglist:
            self.warninglist.remove('Invalid Dir Name')
        
        self.update_dl_ready()

    

    def isValid_url(self, url):

        if re.search(r'https://www\.youtube\.com/.+', url):
            if 'Invalid URL' in self.warninglist:
                self.warninglist.remove('Invalid URL')
        
        else:
            if 'Invalid URL' not in self.warninglist:
                self.warninglist.append('Invalid URL')

            self.ui.url_box.setText('')

        self.update_dl_ready()



    def dl_start(self):
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

        try:
            if dirname:
                yt_downloader(url, isplaylist=isplaylist, callback=self.show_progress).download(res, dirname)
            else:
                yt_downloader(url, isplaylist=isplaylist, callback=self.show_progress).download(res)

            self.ui.curr_download_text.setText('Download Complete')

        except (KeyError, pytube.exceptions.RegexMatchError):
            self.ui.curr_download_text.setText('PyTube Error')

        except ConnectionResetError:
            self.ui.curr_download_text.setText('Connection Reset. Restarting...')
            self.dl_start()
            return

        except ConnectionError:
            self.ui.curr_download_text.setText('Connection Error')

        except FileNotFoundError:
            self.ui.curr_download_text.setText('ffmpeg Not Installed')
            return

        except urllib.error.URLError:
            self.ui.curr_download_text.setText('No Internet')
            
        except:
            self.ui.curr_download_text.setText('Unexpected Error')
            traceback.print_exc()


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


    def show_progress(self, stream, chunk, bytes_remaining):

        self.app.processEvents()

        progress = round((((stream.filesize - bytes_remaining) / stream.filesize) * 100), 2)
        print(f'Downloading: {stream.title} || {progress}')

        if stream.type == 'video':
            title = f'[video] {stream.title}'
        else:
            if progress < 99:
                title = f'[audio] {stream.title}'
            else:
                title = f'[compiling] {stream.title}'

            
        self.ui.progress_text.setText(f'{progress} %')

        if len(title) > 30:
            title = title[:29] + '...'

        self.ui.curr_download_text.setText(title)


def main():
    os.chdir(os.path.dirname(sys.argv[0]))
    app = qtw.QApplication(sys.argv)
    window = MainWindow(app)

    print("Loading UI. Please wait.")

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()





