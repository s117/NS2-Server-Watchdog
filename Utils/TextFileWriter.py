# encoding: utf-8

import os
import time


class TextFileWriter:
    __LOG_STORAGE_DIR = u"./log"
    __LOG_FILE_PATTERN = u"%s-Watchdog-log"
    __LOG_DATE_PATTERN = '%Y-%m-%d_%H-%M-%S'
    __LOG_ENCODING = 'utf-8'

    def __init__(self):
        if not (os.path.exists(TextFileWriter.__LOG_STORAGE_DIR) and os.path.isdir(TextFileWriter.__LOG_STORAGE_DIR)):
            os.mkdir(TextFileWriter.__LOG_STORAGE_DIR)
        log_file_std_name = TextFileWriter.__LOG_FILE_PATTERN % time.strftime(TextFileWriter.__LOG_DATE_PATTERN,
                                                                              time.localtime(time.time()))
        log_file_std_name = TextFileWriter.__LOG_STORAGE_DIR + u"/" + log_file_std_name

        log_file_actual_name = log_file_std_name + u".txt"

        if os.path.exists(log_file_actual_name):
            # log file name conflict
            no = 1
            while os.path.exists(log_file_actual_name):
                log_file_actual_name = u"%s_(%d).txt" % (log_file_std_name, no)
                no = no + 1

        self.__log_file = open(log_file_actual_name, 'w')

    def __del__(self):
        self.__log_file.flush()
        self.__log_file.close()

    def log(self, text):
        if isinstance(text, unicode):
            text = text.encode(TextFileWriter.__LOG_ENCODING)
        elif not isinstance(text, str):
            raise TypeError("text should be either unicode or str")

        self.__log_file.write(text)
        self.__log_file.flush()
