# encoding: utf-8
import os
import time


class TextfileWriter:
    __LOG_STORAGE_DIR = './log'
    __LOG_FILE_PATTERN = '%s-Watchdog-log'
    __LOG_DATE_PATTERN = '%Y-%m-%d_%H-%M-%S'

    def __init__(self):
        if not (os.path.exists(TextfileWriter.__LOG_STORAGE_DIR) and os.path.isdir(TextfileWriter.__LOG_STORAGE_DIR)):
            os.mkdir(TextfileWriter.__LOG_STORAGE_DIR, 0o666)
        log_file_std_name = TextfileWriter.__LOG_FILE_PATTERN % time.strftime(TextfileWriter.__LOG_DATE_PATTERN,
                                                                              time.localtime(time.time()))
        log_file_std_name = TextfileWriter.__LOG_STORAGE_DIR + "/" + log_file_std_name

        log_file_actual_name = log_file_std_name + ".txt"

        if os.path.exists(log_file_actual_name):
            # log file name conflict
            no = 1
            while os.path.exists(log_file_actual_name):
                log_file_actual_name = "%s_(%d).txt" % (log_file_std_name, no)
                no = no + 1

        self.__log_file = open(log_file_actual_name, "w")

    def __del__(self):
        self.__log_file.flush()
        self.__log_file.close()

    def log(self, text):
        self.__log_file.write(unicode(text).encode("utf-8"))
        self.__log_file.flush()
