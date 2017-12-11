#  -*- encoding:UTF-8 -*-
#
# NS2 Server Watch dog -- a Natural Selection 2 server monitoring script
#
#
# Requires Python 2.7
#
# Wrote by John <admin@0x10c.pw>
# MIT License.

import datetime
import json
import locale
import os
import platform
import shlex
import shutil
import signal
import sys
import time
from subprocess import Popen

import psutil

from Utils.TextFileWriter import TextFileWriter

if cmp(platform.system(), 'Windows') is 0:
    from Utils.WindowsConsoleWriter import WindowsConsoleWriter as PlatformConsoleWriter
    from subprocess import CREATE_NEW_PROCESS_GROUP
else:
    from Utils.UnixConsoleWriter import UnixConsoleWriter as PlatformConsoleWriter

VERBOSE_LEVEL = 0
ExitFlag = False


class Logger:
    __TIME_LABEL_PATTERN = '%m/%d/%y-%H:%M:%S'
    __console_writer = PlatformConsoleWriter()
    __file_logger = TextFileWriter()
    __LINE_PATTERN = u"[%s] <%s>: %s\n"

    @staticmethod
    def init_logger():
        global VERBOSE_LEVEL
        VERBOSE_LEVEL = ConfigManager.get_config('verbose_level')

    def __init__(self):
        raise NotImplementedError(u"This class should never be instantiated.")

    @staticmethod
    def __gen_log_line(str_level, text):
        log_line = Logger.__LINE_PATTERN % (time.strftime(Logger.__TIME_LABEL_PATTERN, time.localtime(time.time())),
                                            str_level, text)
        return log_line

    @staticmethod
    def debug(text):
        if VERBOSE_LEVEL >= 2:
            log_line = Logger.__gen_log_line(u"DEBUG", text)
            Logger.__console_writer.debug(log_line)
            Logger.__file_logger.log(log_line)

    @staticmethod
    def verbose(text):
        if VERBOSE_LEVEL >= 1:
            log_line = Logger.__gen_log_line(u"VERBOSE", text)
            Logger.__console_writer.verbose(log_line)
            Logger.__file_logger.log(log_line)

    @staticmethod
    def info(text):
        log_line = Logger.__gen_log_line(u"INFO", text)
        Logger.__console_writer.normal(log_line)
        Logger.__file_logger.log(log_line)

    @staticmethod
    def warn(text):
        log_line = Logger.__gen_log_line(u"WARN", text)
        Logger.__console_writer.warn(log_line)
        Logger.__file_logger.log(log_line)

    @staticmethod
    def fatal(text, exitcode=-1):
        log_line = Logger.__gen_log_line(u"FATAL", text)
        Logger.__console_writer.error(log_line)
        Logger.__file_logger.log(log_line)

        log_line = Logger.__gen_log_line(u"FATAL", (u"Program terminated, exit code: %d." % exitcode))
        Logger.__console_writer.error(log_line)
        Logger.__file_logger.log(log_line)

        sys.exit(exitcode)


class ConfigManager:
    __CONFIG_FILENAME = u"config.json"
    __DEFAULT_CONFIG = {
        # Monitoring interval in second.
        'monitor_interval': 1,

        # Check whether the lua engine is still alive or not by utilizing the helper mod (mod_id=44AE3979).
        'lua_engine_check_status': True,

        # Lua engine unresponsive tolerance (in seconds).
        # PS: DO NOT set it too low, because the helper mod will stop update the record during the initializing &
        #     map changing. If the threshold is too low, the server would get interrupted when performing those action.
        'lua_engine_no_response_threshold': 60,

        # Date format of the helper mod's output.
        'lua_engine_helper_mod_record_format': u"%m/%d/%y %H:%M:%S",

        # Whether restart the server every day.
        'daily_restart': True,

        # When to restart the server? (24h, [hh, mm, ss], local time).
        'daily_restart_h_m_s': [04, 00, 00],

        # The server will only get restarted if the memory usage exceeds this threshold
        # (in byte). Set it to 0 if you always want the restart to get triggered.
        'daily_restart_vms_threshold': 768 * 1024 * 1024,

        # When designating a path, if you give a relative path, it will be expended according to the running cwd
        # NS2Server's root path
        'server_config_executable_path': u"C:/NS2Server",  # or "/opt/NS2Server/serverfiles" for example

        # The name of the server's executable file.
        'server_config_executable_name': u"Server.exe",  # or "server_linux" for linux

        # Path to server config dir.
        'server_config_dir_cfg': u"./server_data/ns2server_configs",

        # Path to server mod storage dir.
        'server_config_dir_mod': u"./server_data/ns2server_mods",

        # Path to server log dir.
        'server_config_dir_log': u"./server_data/ns2server_logs_running",

        # Path to archive the past server info
        'server_config_dir_log_archive': u"./server_data/ns2server_logs_archive",

        # Additional launch option.
        'server_config_extra_parameter':
            u"-name 'Test' -port 27015 -map 'ns2_veil' -limit 20 -speclimit 4 -mods '44AE3979'",

        # Output verbose level, 0 for lowest and 2 for highest.
        'verbose_level': 1
    }

    __config = None

    def __init__(self):
        raise NotImplementedError(u"This class should never be instantiated.")

    @staticmethod
    def get_config(key):
        if ConfigManager.__config is None:
            ConfigManager.load_config()
        return ConfigManager.__config[key]

    @staticmethod
    def save_config():
        with open(ConfigManager.__CONFIG_FILENAME, 'w') as f:
            content = json.dumps(ConfigManager.__config, indent=4, sort_keys=True, encoding='utf-8', ensure_ascii=False)
            f.write(content.encode('utf-8'))
        Logger.info(u"Flushed config to '%s'" % ConfigManager.__CONFIG_FILENAME)

    @staticmethod
    def load_config():
        ConfigManager.__config = {}
        if os.path.exists(ConfigManager.__CONFIG_FILENAME):
            Logger.info(u"Loading config from file '%s'" % ConfigManager.__CONFIG_FILENAME)
            with open(ConfigManager.__CONFIG_FILENAME) as json_file:
                try:
                    json_data = json.load(json_file, encoding='utf-8')
                except ValueError:
                    Logger.fatal(u"Invalid config.json, please check it.")
                else:
                    for i, v in ConfigManager.__DEFAULT_CONFIG.items():
                        if i in json_data:
                            ConfigManager.__config[i] = json_data[i]
                        else:
                            ConfigManager.__config[i] = ConfigManager.__DEFAULT_CONFIG[i]
        else:
            Logger.info(u"File '%s' not found, a new one will be created" % ConfigManager.__CONFIG_FILENAME)
            ConfigManager.__config = ConfigManager.__DEFAULT_CONFIG
        ConfigManager.save_config()
        Logger.info(u"Config loaded")


class ServerProcessHandler:
    __WAIT_TIME_BEFORE_FORCE_KILL = 5
    __WAIT_TIME_BEFORE_GIVE_UP = 60

    def __init__(self):
        self.__server_root = ConfigManager.get_config('server_config_executable_path')
        if not os.path.isabs(self.__server_root):
            Logger.warn(u"You are using relative path '%s' to specify the server root" % self.__server_root)
            self.__server_root = os.path.abspath(self.__server_root)
            Logger.warn(
                u"DOUBLE CHECK: The absolute path for the server root is '%s'. Is that correct?" % self.__server_root)

        if not os.path.isdir(self.__server_root):
            Logger.fatal(u"The root of NS2Server ('%s') does not exist" % self.__server_root)

        key_dir = ['server_config_dir_cfg', 'server_config_dir_mod',
                   'server_config_dir_log', 'server_config_dir_log_archive']
        for kd in key_dir:
            vd = ConfigManager.get_config(kd)
            if not os.path.isdir(vd):
                Logger.fatal(
                    u"Fail to start server, because directory '%s' does not exist (value of '%s')" % (vd, kd))
            if not os.path.isabs(vd):
                Logger.warn(u"You are using relative path '%s' for config '%s')" % (vd, kd))

                Logger.warn(u"DOUBLE CHECK: The absolute path for the config '%s' is '%s'. Is that correct?" % (
                    kd, os.path.abspath(vd)))

        self.__server_dir_cfg = os.path.abspath(ConfigManager.get_config('server_config_dir_cfg'))
        self.__server_dir_mod = os.path.abspath(ConfigManager.get_config('server_config_dir_mod'))
        self.__server_dir_log = os.path.abspath(ConfigManager.get_config('server_config_dir_log'))
        self.__server_dir_log_backup = os.path.abspath(ConfigManager.get_config('server_config_dir_log_archive'))

        sub_dir = u"/x64/"
        if cmp(platform.architecture()[0], '64bit') is not 0:
            Logger.fatal(u"You are running 32bit OS, which is not supported by NS2DS anymore. Consider upgrading.")

        executable_path = self.__server_root + sub_dir + ConfigManager.get_config('server_config_executable_name')
        if not os.path.isfile(executable_path):
            Logger.fatal(u"Fail to start server, because executable file '%s' does not exist" % executable_path)

        if not os.access(executable_path, os.X_OK):
            Logger.fatal(u"You have no execute privilege on server's executable image: %s" % executable_path)

        param = [executable_path, u"-config_path", self.__server_dir_cfg, u"-modstorage", self.__server_dir_mod,
                 u"-logdir", self.__server_dir_log]

        self.__param = param + shlex.split(ConfigManager.get_config('server_config_extra_parameter').encode('utf-8'))

        self.__pid = -1
        self.__process = None
        self.__ps = None
        self.__ps_cmdline = None
        self.__ps_create_time = 0.0

    def get_server_abs_root(self):
        return self.__server_root

    def get_server_abs_cfg_dir(self):
        return self.__server_dir_cfg

    def get_server_abs_mod_dir(self):
        return self.__server_dir_mod

    def get_server_abs_log_dir(self):
        return self.__server_dir_log

    def restart_server(self):
        self.stop_server()
        self.start_server()

    def start_server(self):
        self.__force_update_helper_mod_record()
        if not self.is_running():
            self.__archive_log_and_dmp()

            prev_dir = os.getcwd()
            os.chdir(self.get_server_abs_root())

            try:
                cmdline = u""
                for p in self.__param:
                    if type(p) is str:
                        p = p.decode('utf-8')
                    if u" " in p:
                        p = u"\"" + p + u"\""
                    cmdline = cmdline + p + u" "

                cmdline = cmdline

                Logger.info(u"Starting server using cmdline:'%s'" % cmdline)

                # cmdline = cmdline.encode(locale.getdefaultlocale()[1])
                with open(os.devnull, 'w') as DEVNULL:
                    if cmp(platform.system(), 'Windows') is 0:
                        # Start server under the Windows
                        self.__process = Popen(cmdline.encode('utf-8'),
                                               stdin=DEVNULL,
                                               stdout=DEVNULL,
                                               stderr=DEVNULL,
                                               cwd=self.get_server_abs_root(),
                                               creationflags=CREATE_NEW_PROCESS_GROUP)
                    else:
                        # Start server under the Linux
                        self.__process = Popen(
                            args=cmdline.encode('utf-8'),
                            shell=True,
                            close_fds=True,
                            stdin=DEVNULL,
                            stdout=DEVNULL,
                            stderr=DEVNULL,
                            cwd=self.get_server_abs_root())

                self.__pid = self.__process.pid
                self.__ps = psutil.Process(pid=self.__pid)
                self.__ps_create_time = self.__ps.create_time()
                self.__ps_cmdline = cmdline
                # self.__ps_cmdline = u""
                # for i in self.__ps.cmdline():
                #     if type(i) is str:
                #         # i = i.decode(locale.getdefaultlocale()[1])
                #         i = i.decode('utf-8')
                #     self.__ps_cmdline = self.__ps_cmdline + i + u" "

            except psutil.NoSuchProcess:
                self.__pid = -1
                self.__process = None
                self.__ps = None
                self.__ps_cmdline = None
                Logger.fatal(u"Fail to start the server, please check the setting or the server's integrity")
            except psutil.AccessDenied:
                Logger.fatal(u"Access denied when try to control the server process (pid %d)" % self.__pid)
            else:
                Logger.info(u"Server is running, pid=%d" % self.__pid)

            os.chdir(prev_dir)

    def stop_server(self):
        if self.is_running():
            try:
                Logger.info(u"Try to stop server process (pid %d) by terminate()" % self.__pid)
                self.__ps.terminate()
                try:
                    self.__ps.wait(self.__WAIT_TIME_BEFORE_FORCE_KILL)
                    Logger.info(u"Server process (pid %d) get terminated" % self.__pid)
                except psutil.TimeoutExpired:
                    Logger.warn(u"Fail to stop server process (pid %d) by terminate(), trying kill()" % self.__pid)
                    try:
                        self.__ps.kill()
                        self.__ps.wait(self.__WAIT_TIME_BEFORE_GIVE_UP)
                        Logger.info(u"Server process (pid %d) get killed" % self.__pid)
                    except psutil.TimeoutExpired:
                        Logger.fatal(u"Fail to terminate server process (pid %d)" % self.__pid)

            except psutil.NoSuchProcess:
                Logger.info(u"Server process (pid %s) already get stopped" % self.__pid)
            except psutil.AccessDenied:
                Logger.fatal(u"Access denied when try to control the server process (pid %d)" % self.__pid)

            Logger.info(u"Stop server process (pid %d) successfully" % self.__pid)

            self.__pid = -1
            self.__process = None
            self.__ps = None
            self.__ps_cmdline = None

    def is_running(self):
        try:
            if (self.__pid is not -1) and \
                    (self.__process.poll() is None) and \
                    (self.__ps.is_running()):
                return True
        except psutil.NoSuchProcess:
            pass
        return False

    def get_info(self):
        if self.is_running():
            try:
                vms = self.__ps.memory_info().vms

            except psutil.NoSuchProcess:
                return None
            except psutil.AccessDenied:
                Logger.fatal(u"Access denied when try to control the server process (pid %d)" % self.__pid)
            else:
                return {
                    'pid': self.__pid,
                    'vms': vms,
                    'create_time': self.__ps_create_time,
                }

    def __force_update_helper_mod_record(self):
        # The helper mod's record need to be updated before start because otherwise
        # the launching progress will be disturbed by the lua engine check.
        DEFAULT_PING_MODE_NAME = u"server_modding_ping.txt"
        ABS_PATH_PING_MODE_TXT = self.get_server_abs_cfg_dir() + u"/" + DEFAULT_PING_MODE_NAME
        try:
            expire_time = time.time() + ConfigManager.get_config('lua_engine_no_response_threshold')

            st = time.strftime(ConfigManager.get_config('lua_engine_helper_mod_record_format'),
                               time.localtime(expire_time))
            with open(ABS_PATH_PING_MODE_TXT, 'w') as f:
                f.write(st)
        except IOError:
            Logger.fatal(u"Fail to force update the helper mod's record, check user permission")
        else:
            Logger.verbose(u"Force updated the helper mod's record, value: '%s'" % st)

    def __archive_log_and_dmp(self):

        time_label = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(time.time()))

        new_archive_dir = self.__server_dir_log_backup + u"/" + time_label
        i = 1
        while os.path.exists(new_archive_dir):
            new_archive_dir = self.__server_dir_log_backup + u"/" + time_label + u"_(%d)" % i
            i = i + 1
        try:
            os.mkdir(new_archive_dir)
        except Exception:
            Logger.fatal(u"Fail to create new folder for archive, check user permission)")
        else:
            # retry wait time after fail to move files from running folder to archive folder, in seconds
            retry_wait_sec = 5
            retry_flag = True
            global ExitFlag
            while retry_flag:
                Logger.verbose(u"Trying to archive previous process's running history from '%s' to '%s'..." % (
                    self.__server_dir_log, new_archive_dir))
                if ExitFlag:
                    Logger.fatal(u"Script get terminated while trying to archive the server's running log.")
                try:
                    log_dir_files = os.listdir(self.__server_dir_log)
                except Exception:
                    Logger.fatal(u"Fail to list the running log folder, check user permission)")
                else:
                    try:
                        for file in log_dir_files:
                            file_full_path = self.__server_dir_log + u"/" + file
                            shutil.move(file_full_path, new_archive_dir + u"/" + os.path.basename(file))
                    except Exception:
                        Logger.warn(
                            u"Archive failed. (Maybe the bug collector or previous server process is still running?)")
                        Logger.warn(u"Retry archiving after %d seconds." % retry_wait_sec)
                        try:
                            time.sleep(retry_wait_sec)
                        except IOError:
                            Logger.debug(u"Archiving retry sleep get interrupted.")
                    else:
                        retry_flag = False
            Logger.verbose(u"Previous process's running history has archived to '%s'." % new_archive_dir)


class ServerWatchDog:
    def __init__(self):
        self.__server = ServerProcessHandler()
        self.__monitor_interval = ConfigManager.get_config('monitor_interval')
        self.__is_daily_restart_server = ConfigManager.get_config('daily_restart')
        self.__daily_restart_time_hms = ConfigManager.get_config('daily_restart_h_m_s')
        self.__daily_restart_vms_threshold = ConfigManager.get_config('daily_restart_vms_threshold')
        self.__next_daily_restart_trigger_time = self.__calc_next_daily_restart_trigger_timestamp()

        self.__is_lua_engine_check_status = ConfigManager.get_config('lua_engine_check_status')
        self.__abspath_helper_mod_output = self.__server.get_server_abs_cfg_dir() + u"/server_modding_ping.txt"
        self.__lua_engine_no_response_threshold = ConfigManager.get_config('lua_engine_no_response_threshold')
        self.__helper_mod_record_pattern = ConfigManager.get_config("lua_engine_helper_mod_record_format")
        self.__helper_mod_output_invalid_cnt = 0

    def run_server(self):
        Logger.info(u"NS2 Server Watchdog script.")
        Logger.info(u"Press Ctrl-C to terminate this script and the running server process.")
        sleep_sec = self.__monitor_interval
        self.__server.start_server()
        while not ExitFlag:
            if self.__is_server_process_missing() or \
                    self.__is_need_daily_restart() or \
                    self.__is_server_lua_engine_dead():
                self.__server.restart_server()
            try:
                time.sleep(sleep_sec)
            except IOError:
                Logger.debug(u"Main loop met IOError during sleep.")
        self.__server.stop_server()

    def __is_server_process_missing(self):
        PREFIX_STRING = u"Process monitor: "
        if self.__server.is_running():
            Logger.debug(PREFIX_STRING + u"process alive")
            return False
        else:
            Logger.info(PREFIX_STRING + u"unexpected server shutdown detected, restoring...")
            return True

    def __is_need_daily_restart(self):
        if not self.__is_daily_restart_server:
            return False

        PREFIX_STRING = u"Daily restart: "
        if time.time() >= self.__next_daily_restart_trigger_time:
            Logger.info(PREFIX_STRING + u"now is the time to restart")
            self.__next_daily_restart_trigger_time = self.__calc_next_daily_restart_trigger_timestamp()
            process_info = self.__server.get_info()
            if process_info is not None:
                if process_info['vms'] < self.__daily_restart_vms_threshold:
                    Logger.info(PREFIX_STRING + u"server will not get restarted (vms/%d < threshold/%d" % (
                        process_info['vms'], self.__daily_restart_vms_threshold))
                    return False
                else:
                    Logger.info(PREFIX_STRING + u"server will get restarted (vms/%d >= threshold/%d)" % (
                        process_info['vms'], self.__daily_restart_vms_threshold))
                    return True
            else:
                Logger.info(PREFIX_STRING + u"server will get restarted (server process stopped)")
                return True
        else:  # not now
            return False

    def __is_server_lua_engine_dead(self):
        if not self.__is_lua_engine_check_status:
            return False

        st = u"uninitialized"
        is_dead = False
        exception_flag = False
        exception_msg = ""
        PREFIX_STRING = u"Lua engine check: "
        try:
            with open(self.__abspath_helper_mod_output, 'r') as f:
                st = f.readline()
            last_update_time = datetime.datetime.strptime(st, self.__helper_mod_record_pattern)
            last_update_timestamp = time.mktime(last_update_time.timetuple())
        except IOError:
            exception_flag = True
            exception_msg = u"Fail to open helper mod's output: '%s'." % (
                self.__abspath_helper_mod_output)
        except ValueError:
            exception_flag = True
            exception_msg = u"Fail to parse the helper mod's record '%s' with pattern %s." % (
                st, self.__helper_mod_record_pattern)
        except TypeError:
            exception_flag = True
            exception_msg = u"Fail to parse the helper mod's record because the file includes invalid character."
        else:
            # successfully parsed the helper mod's record
            self.__helper_mod_output_invalid_cnt = 0
            engine_frozen_time = int(time.time() - last_update_timestamp)
            if engine_frozen_time > self.__lua_engine_no_response_threshold:
                Logger.info(
                    PREFIX_STRING +
                    (u"Lua engine has frozen for %d second(s), the server will be restarted" % engine_frozen_time))
                is_dead = True
            else:
                Logger.debug(
                    PREFIX_STRING +
                    (u"Lua engine check: OK, frozen_time = %d, threshold = %d" % (
                        engine_frozen_time, self.__lua_engine_no_response_threshold)))
                is_dead = False
        finally:
            if exception_flag:
                # fail to parse the helper mod's record
                self.__helper_mod_output_invalid_cnt = self.__helper_mod_output_invalid_cnt + 1
                actual_passed_time = self.__helper_mod_output_invalid_cnt * self.__monitor_interval
                if actual_passed_time < self.__lua_engine_no_response_threshold:
                    Logger.warn(
                        PREFIX_STRING + exception_msg +
                        (u" Assume engine is good (%ds/%ds)" % (
                            actual_passed_time, self.__lua_engine_no_response_threshold)))
                    is_dead = False
                else:
                    Logger.warn(
                        PREFIX_STRING + exception_msg +
                        (u" Assume engine is down (%ds/%ds)" % (
                            actual_passed_time, self.__lua_engine_no_response_threshold)))
                    is_dead = True

        return is_dead

    def __calc_next_daily_restart_trigger_timestamp(self):
        time_now_timestamp = time.time()
        time_now = time.localtime(time_now_timestamp)
        delta_one_day = datetime.timedelta(days=1)

        trigger_time_today = datetime.datetime(time_now.tm_year, time_now.tm_mon, time_now.tm_mday,
                                               self.__daily_restart_time_hms[0],
                                               self.__daily_restart_time_hms[1],
                                               self.__daily_restart_time_hms[2])
        trigger_time_tomorrow = trigger_time_today + delta_one_day

        trigger_time_today_unix_timestamp = time.mktime(trigger_time_today.timetuple())
        trigger_time_tomorrow_unix_timestamp = time.mktime(trigger_time_tomorrow.timetuple())

        if time_now_timestamp < trigger_time_today_unix_timestamp:
            return trigger_time_today_unix_timestamp
        else:
            return trigger_time_tomorrow_unix_timestamp


def main(argv):
    server_wdt = ServerWatchDog()
    server_wdt.run_server()


def signal_handler(sig, frame):
    global ExitFlag
    if sig == signal.SIGINT:
        Logger.info(u"Captured signal SIGINT, prepare to exit")
        ExitFlag = True


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    Logger.init_logger()
    main(sys.argv)
