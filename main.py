#coding=utf-8
import argparse
import functools
import os
import shutil
import signal
import subprocess
import sys


class TimeoutError(Exception):
    pass

def timeout(seconds, error_message="Timeout Error"):
    def decorated(func):
        result = ""

        def _handle_timeout(signum, frame):
            global result
            result = error_message
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            global result
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return functools.wraps(func)(wrapper)
    return decorated


class Rabbit(object):

    def _format_size(self, size_str):
        try:
            if "MiB" in size_str:
                return float(size_str.replace("MiB", "")) * 1024
            elif "KiB" in size_str:
                return float(size_str.replace("KiB", ""))
            return 0
        except:
            return 0

    def _clean_carrot(self, details):
        remove_list = ["", ",", "@"]
        cleaned_details = []
        for item in details:
            if item not in remove_list:
                cleaned_details.append(item)
        return cleaned_details

    def read_details(self, details):
        details = self._clean_carrot(details)
        info = {}
        try:
            info['id'] = int(details[0])
            info['type'] = details[1]
            info['is_audio'] = 'audio' in details
            info['is_video'] = 'video' in details
            if info['is_audio']:
                info['size'] = self._format_size(details[-1])
                info['audio_type'] = details[-3]
            elif info['is_video']:
                info['resolution'] = details[2]
                info['size'] = self._format_size(details[-1])
            else:
                return {}
            return info
        except:
            return {}

    @timeout(5)
    def _get_carrots_with_mud(self, url):
        try:
            encode_command = "youtube-dl -F %s" % url
            output = subprocess.check_output(encode_command.split(), stderr=subprocess.STDOUT)
            carrots_with_mud = output.split("\n")[4:]
            return carrots_with_mud
        except Exception as err:
            print "url: %s cannot get, err:%s" % (url, err)
            return []

    def get_carrots_with_mud(self, url, retries=3):
        retry = 0
        while retry < retries:
            carrots_with_mud = self._get_carrots_with_mud(url)
            if carrots_with_mud:
                return carrots_with_mud
            retry += 1

    def clean_carrots(self, carrots_with_mud):
        carrots = {
            'videos': [],
            'audios': []
        }
        for carrot in carrots_with_mud:
            details = carrot.split(" ")
            carrot_info = self.read_details(details)
            if not carrot_info:
                continue
            if carrot_info['is_video']:
                carrots['videos'].append(carrot_info)
            elif carrot_info['is_audio']:
                carrots['audios'].append(carrot_info)
        return carrots

    def get_max_carrots(self, carrots):
        max_video_carrot_size = 0
        res_carrot = None
        for carrot in carrots:
            if carrot['size'] > max_video_carrot_size and carrot['type'] == 'webm':
                if carrot['is_audio']:
                    if carrot['audio_type'] != 'opus':
                        continue
                res_carrot = carrot
                max_video_carrot_size = carrot['size']
        return res_carrot

    def download_video(self, dw, url, reties=3):
        retry = 0
        while retry < reties:
            try:
                return subprocess.check_call(["youtube-dl -f %s %s" % (dw, url)], shell=True)
            except Exception as err:
                print "Download video failed, error: %s, dw: %s, url: %s, retry..." % (err, dw, url)
                retry += 1
        return 1

    def rename_file(self, url):
        name = url.split("v=")[1]
        for f in os.listdir(os.getcwd()):
            if ".webm" in f:
                if os.path.isfile(os.path.join(os.getcwd(), f)):
                    os.rename(os.path.join(os.getcwd(), f), '%s.webm' % name)
        return name

    def ffmpeg_to_mp4(self, name, reties=3):
        retry = 0
        while retry < reties:
            try:
                return subprocess.check_call(["ffmpeg -i %s.webm %s.mp4" % (name, name)], shell=True)
            except Exception as err:
                print "ffmpeg_to_mp4 failed, name: %s, error: %s, retry..." % (name, err)
                retry += 1
        return 1

    def run(self, urls):
        print "Rabbit is running!"
        for url in urls:
            try:
                os.mkdir("mp4")
                os.mkdir("webm")
                carrots_with_mud = self.get_carrots_with_mud(url)
                if not carrots_with_mud:
                    continue
                carrots = self.clean_carrots(carrots_with_mud)
                max_video_carrot = self.get_max_carrots(carrots['videos'])
                max_audio_carrot = self.get_max_carrots(carrots['audios'])
                if max_video_carrot and max_audio_carrot:
                    max_video_id = max_video_carrot['id']
                    max_audio_id = max_audio_carrot['id']
                    dw = "%s+%s" % (max_video_id, max_audio_id)
                    if self.download_video(dw, url) == 0:
                        name = self.rename_file(url)
                        self.ffmpeg_to_mp4(name)
                        shutil.move("./%s.mp4" % name, "./mp4/%s.mp4" % name)
                        shutil.move("./%s.webm" % name, "./webm/%s.webm" % name)
            except Exception as err:
                print "url: %s is invalid!, error: %s" % (url, err)


rabbit = Rabbit()

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-f', '--file', required=False, type=str, default='sample_file', help='The name of file with urls')
    args = arg_parser.parse_args(sys.argv[1:])
    with open(args.file, 'r') as f:
        urls = f.readlines()
        urls = [url.replace("\n", "") for url in urls]
    rabbit.run(urls)