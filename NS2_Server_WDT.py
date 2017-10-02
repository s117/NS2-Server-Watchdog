#  -*- encoding:UTF-8 -*-
#
# NS2 Server Watch dog -- a Natural Selection 2 server monitoring script
#
# Wrote by John <admin@0x10c.pw>
# MIT License.

import datetime
import json
import os
import platform
import shlex
import signal
import sys
import time
from subprocess import Popen

import psutil

from Utils.TextfileWriter import TextfileWriter

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
    __file_logger = TextfileWriter()
    __LINE_PATTERN = u"[%s] <%s>: %s\n"

    @staticmethod
    def init_logger():
        global VERBOSE_LEVEL
        VERBOSE_LEVEL = ConfigManager.get_config("verbose_level")

    def __init__(self):
        raise NotImplementedError("This class should never be instantiated.")

    @staticmethod
    def debug(text):
        if VERBOSE_LEVEL >= 2:
            log_line = Logger.__LINE_PATTERN % (time.strftime(Logger.__TIME_LABEL_PATTERN, time.localtime(time.time())),
                                                "DEBUG", unicode(text))
            Logger.__console_writer.debug(log_line)
            Logger.__file_logger.log(log_line)

    @staticmethod
    def verbose(text):
        if VERBOSE_LEVEL >= 1:
            log_line = Logger.__LINE_PATTERN % (time.strftime(Logger.__TIME_LABEL_PATTERN, time.localtime(time.time())),
                                                "VERBOSE", unicode(text))
            Logger.__console_writer.verbose(log_line)
            Logger.__file_logger.log(log_line)

    @staticmethod
    def info(text):
        log_line = Logger.__LINE_PATTERN % (time.strftime(Logger.__TIME_LABEL_PATTERN, time.localtime(time.time())),
                                            "INFO", unicode(text))
        Logger.__console_writer.normal(log_line)
        Logger.__file_logger.log(log_line)

    @staticmethod
    def warn(text):
        log_line = Logger.__LINE_PATTERN % (time.strftime(Logger.__TIME_LABEL_PATTERN, time.localtime(time.time())),
                                            "WARN", unicode(text))
        Logger.__console_writer.warn(log_line)
        Logger.__file_logger.log(log_line)

    @staticmethod
    def fatal(text, exitcode=-1):
        log_line = Logger.__LINE_PATTERN % (time.strftime(Logger.__TIME_LABEL_PATTERN, time.localtime(time.time())),
                                            "FATAL", unicode(text))
        Logger.__console_writer.error(log_line)
        Logger.__file_logger.log(log_line)

        log_line = Logger.__LINE_PATTERN % (time.strftime(Logger.__TIME_LABEL_PATTERN, time.localtime(time.time())),
                                            "FATAL", (u"Program terminated, exit code: %d." % exitcode))
        Logger.__console_writer.error(log_line)
        Logger.__file_logger.log(log_line)
        sys.exit(exitcode)


class ConfigManager:
    __CONFIG_FILENAME = "config.json"
    __DEFAULT_CONFIG = {
        # Monitoring interval in second.
        "monitor_interval": 1,

        # Check whether the lua engine is still alive or not by utilizing the helper mod (mod_id=44AE3979).
        "check_lua_engine_status": True,

        # Lua engine unresponsive tolerance (in seconds).
        # PS: DO NOT set it too low, because the helper mod will stop update the record during the initializing &  
        #     map changing. If the threshold is too low, the server would get interrupted when performing those action.
        "lua_engine_no_response_threshold": 60,

        # Date format of the helper mod's output.
        "format_helper_mod_record": "%m/%d/%y %H:%M:%S",

        # Dump the memory before restart the unresponsive server.
        "create_mem_dump": False,

        # Whether restart the server every day.
        "daily_restart": True,

        # When to restart the server? (24h, [hh, mm, ss], local time).
        "daily_restart_h_m_s": [04, 00, 00],

        # The server will only get restarted if the memory usage exceeds this threshold
        # (in byte). Set it to 0 if you always want the restart to get triggered.
        "daily_restart_vms_threshold": 768 * 1024 * 1024,

        # NS2Server's root path, recommending using a absolute path.
        "server_path": "C:/NS2Server",  # or "/opt/NS2Server/serverfiles" for example

        # The name of the server's executable file.
        "server_executable_image": "Server.exe",  # or "server_linux32" for example

        # Path to server config dir. If you use the relative path, it should be relative to the server's root
        "server_config_cfg_dir": "./configs/ns2server_configs",

        # Path to server log dir. If you use the relative path, it should be relative to the server's root
        "server_config_log_dir": "./configs/ns2server_logs",

        # Path to server mod storage dir. If you use the relative path, it should be relative to the server's root
        "server_config_mod_dir": "./configs/ns2server_mods",

        # Additional launch option.
        "server_config_extra_parameter":
            "-name 'Test' -port 27015 -map 'ns2_veil' -limit 20 -speclimit 4 -mods '44AE3979'",

        # Output verbose level, 0 for lowest and 2 for highest.
        "verbose_level": 2
    }

    __config = None

    def __init__(self):
        raise NotImplementedError("This class should never be instantiated.")

    @staticmethod
    def get_config(key):
        if ConfigManager.__config is None:
            ConfigManager.load_config()
        return ConfigManager.__config[key]

    @staticmethod
    def save_config():
        with open(ConfigManager.__CONFIG_FILENAME, 'w') as f:
            content = json.dumps(ConfigManager.__config, indent=4, sort_keys=True, encoding="utf-8", ensure_ascii=False)
            f.write(content.encode("utf-8"))
        Logger.info("Flushed config to '%s'" % ConfigManager.__CONFIG_FILENAME)

    @staticmethod
    def load_config():
        ConfigManager.__config = {}
        if os.path.exists(ConfigManager.__CONFIG_FILENAME):
            Logger.info("Loading config from file '%s'" % ConfigManager.__CONFIG_FILENAME)
            with open(ConfigManager.__CONFIG_FILENAME) as json_file:
                try:
                    json_data = json.load(json_file, encoding="utf-8")
                except ValueError:
                    Logger.fatal("Invalid config.json, please check it.")
                else:
                    for i, v in ConfigManager.__DEFAULT_CONFIG.items():
                        if i in json_data:
                            ConfigManager.__config[i] = json_data[i]
                        else:
                            ConfigManager.__config[i] = ConfigManager.__DEFAULT_CONFIG[i]
        else:
            Logger.info("File '%s' not found, a new one will be created" % ConfigManager.__CONFIG_FILENAME)
            ConfigManager.__config = ConfigManager.__DEFAULT_CONFIG
        ConfigManager.save_config()
        Logger.info("Config loaded")


class ServerProcessHandler:
    __WAIT_TIME_BEFORE_FORCE_KILL = 5
    __WAIT_TIME_BEFORE_GIVE_UP = 60

    def __init__(self):
        self.__server_root = ConfigManager.get_config("server_path")
        if not os.path.isabs(self.__server_root):
            Logger.warn("You are using relative path '%s' to specify the server root" % self.__server_root)
            self.__server_root = os.path.abspath(self.__server_root)
            Logger.warn(
                "DOUBLE CHECK: The absolute path for the server root is '%s'. Is that correct?" % self.__server_root)

        if not os.path.isdir(self.__server_root):
            Logger.fatal("The root of NS2Server ('%s') does not exist" % self.__server_root)

        prev_dir = os.getcwd()
        os.chdir(self.__server_root)

        param = []
        key_dir = ["server_config_cfg_dir", "server_config_log_dir", "server_config_mod_dir"]
        for kd in key_dir:
            vd = ConfigManager.get_config(kd)
            if not os.path.isdir(vd):
                Logger.fatal(
                    "Fail to start server, because directory '%s' does not exist (value of '%s')" % (vd, kd))
            if not os.path.isabs(vd):
                Logger.warn("You are using relative path '%s' for config '%s')" % (vd, kd))

                Logger.warn("DOUBLE CHECK: The absolute path for the config '%s' is '%s'. Is that correct?" % (
                    kd, convert_rel_path_to_abs_path(self.__server_root, vd)))
        executable_path = self.__server_root + "/" + ConfigManager.get_config("server_executable_image")
        if not os.path.isfile(executable_path):
            Logger.fatal("Fail to start server, because executable file '%s' does not exist" % executable_path)

        param.append(executable_path)
        if not os.access(executable_path, os.X_OK):
            Logger.fatal("You have no execute privilege on server's executable image: %s" % executable_path)

        param.append("-config_path")
        param.append(ConfigManager.get_config("server_config_cfg_dir"))

        param.append("-modstorage")
        param.append(ConfigManager.get_config("server_config_mod_dir"))

        param.append("-logdir")
        param.append(ConfigManager.get_config("server_config_log_dir"))

        self.__param = param + shlex.split(ConfigManager.get_config("server_config_extra_parameter").encode('utf8'))

        self.__pid = -1
        self.__process = None
        self.__ps = None
        self.__ps_cmdline = None
        self.__ps_create_time = 0.0

        os.chdir(prev_dir)

    def get_server_abs_root(self):
        return self.__server_root

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
                    if type(p) is not unicode:
                        p = p.decode('utf-8')
                    if " " in p:
                        p = u"\"" + p + u"\""
                    cmdline = cmdline + p + u" "

                Logger.info(u"Starting server using cmdline:'%s'" % cmdline)

                # cmdline = cmdline.encode(locale.getdefaultlocale()[1])
                with open(os.devnull, "w") as DEVNULL:
                    if cmp(platform.system(), 'Windows') is 0:
                        # Start server under the Windows
                        self.__process = Popen(cmdline.encode("utf-8"),
                                               stdin=DEVNULL,
                                               stdout=DEVNULL,
                                               stderr=DEVNULL,
                                               cwd=self.get_server_abs_root(),
                                               creationflags=CREATE_NEW_PROCESS_GROUP)
                    else:
                        # Start server under the Linux
                        self.__process = Popen(
                            args=cmdline,
                            shell=True,
                            close_fds=True,
                            stdin=DEVNULL,
                            stdout=DEVNULL,
                            stderr=DEVNULL,
                            cwd=self.get_server_abs_root())

                self.__pid = self.__process.pid
                self.__ps = psutil.Process(pid=self.__pid)
                self.__ps_cmdline = ""
                self.__ps_create_time = self.__ps.create_time()

                Logger.debug("Process's cmdline: %s" % str(self.__ps.cmdline()))

                for i in self.__ps.cmdline():
                    self.__ps_cmdline = self.__ps_cmdline + i + " "

            except psutil.NoSuchProcess:
                self.__pid = -1
                self.__process = None
                self.__ps = None
                self.__ps_cmdline = None
                Logger.fatal("Fail to start the server, please check the setting or the server's integrity")
            except psutil.AccessDenied:
                Logger.fatal("Access denied when try to control the server process (pid %d)" % self.__pid)
            else:
                Logger.info("Server is running, pid=%d" % self.__pid)

            os.chdir(prev_dir)

    def stop_server(self):
        if self.is_running():
            try:
                Logger.info("Try to stop server process (pid %d) by terminate()" % self.__pid)
                self.__ps.terminate()
                try:
                    self.__ps.wait(self.__WAIT_TIME_BEFORE_FORCE_KILL)
                    Logger.info("Server process (pid %d) get terminated" % self.__pid)
                except psutil.TimeoutExpired:
                    Logger.warn("Fail to stop server process (pid %d) by terminate(), trying kill()" % self.__pid)
                    try:
                        self.__ps.kill()
                        self.__ps.wait(self.__WAIT_TIME_BEFORE_GIVE_UP)
                        Logger.info("Server process (pid %d) get killed" % self.__pid)
                    except psutil.TimeoutExpired:
                        Logger.fatal("Fail to terminate server process (pid %d)" % self.__pid)

            except psutil.NoSuchProcess:
                Logger.info("Server process (pid %s) already get stopped" % self.__pid)
            except psutil.AccessDenied:
                Logger.fatal("Access denied when try to control the server process (pid %d)" % self.__pid)

            Logger.info("Stop server process (pid %d) successfully" % self.__pid)

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
                Logger.fatal("Access denied when try to control the server process (pid %d)" % self.__pid)
            else:
                return {
                    "pid": self.__pid,
                    "vms": vms,
                    "create_time": self.__ps_create_time,
                }

    def __force_update_helper_mod_record(self):
        # The helper mod's record need to be updated before start because otherwise
        # the launching progress will be disturbed by the lua engine check.
        DEFAULT_PING_MODE_NAME = "server_modding_ping.txt"
        ABS_SERVER_CONFIG_DIR = convert_rel_path_to_abs_path(self.get_server_abs_root(),
                                                             ConfigManager.get_config("server_config_cfg_dir"))
        ABS_PATH_PING_MODE_TXT = ABS_SERVER_CONFIG_DIR + "/" + DEFAULT_PING_MODE_NAME
        try:
            expire_time = time.time() + ConfigManager.get_config("lua_engine_no_response_threshold")

            st = time.strftime(ConfigManager.get_config("format_helper_mod_record"), time.localtime(expire_time))
            with open(ABS_PATH_PING_MODE_TXT, 'w') as f:
                f.write(st)
        except IOError:
            Logger.fatal("Fail to force update the helper mod's record, check user permission")
        else:
            Logger.verbose("Force updated the helper mod's record, value: '%s'" % st)

    def __archive_log_and_dmp(self):
        DEFAULT_LOG_FILE_NAME = "log-Server.txt"
        DEFAULT_DUMP_FILE_NAME = "lastcrash.dmp"

        time_label = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(time.time()))

        prev_dir = os.getcwd()
        os.chdir(self.get_server_abs_root())
        os.chdir(ConfigManager.get_config("server_config_log_dir"))

        try:
            if os.path.exists(DEFAULT_DUMP_FILE_NAME):
                os.rename(DEFAULT_DUMP_FILE_NAME, time_label + "_" + DEFAULT_DUMP_FILE_NAME)
                Logger.verbose("Archived the crash dump: '%s' -> '%s'" % (
                    DEFAULT_DUMP_FILE_NAME, time_label + "_" + DEFAULT_DUMP_FILE_NAME))
        except Exception:
            Logger.fatal("Fail to archive the crash dump file. (Maybe the last server process is still running?)")

        try:
            if os.path.exists(DEFAULT_LOG_FILE_NAME):
                os.rename(DEFAULT_LOG_FILE_NAME, time_label + "_" + DEFAULT_LOG_FILE_NAME)
                Logger.verbose("Archived the server log: '%s' -> '%s'" % (
                    DEFAULT_LOG_FILE_NAME, time_label + "_" + DEFAULT_LOG_FILE_NAME))
        except Exception:
            Logger.fatal("Fail to archive the server log file. (Maybe the last server process is still running?)")
        os.chdir(prev_dir)


def convert_rel_path_to_abs_path(root_path, rel_path):
    prev_dir = os.getcwd()
    os.chdir(root_path)
    abs_path = os.path.abspath(rel_path)
    os.chdir(prev_dir)
    return abs_path


class ServerWatchDog:
    def __init__(self):
        self.__server = ServerProcessHandler()
        self.__is_daily_restart_server = ConfigManager.get_config("daily_restart")
        self.__daily_restart_time_hms = ConfigManager.get_config("daily_restart_h_m_s")
        self.__daily_restart_vms_threshold = ConfigManager.get_config("daily_restart_vms_threshold")
        self.__next_daily_restart_trigger_time = self.__calc_next_daily_restart_trigger_timestamp()

        self.__is_check_lua_engine_status = ConfigManager.get_config("check_lua_engine_status")
        abspath_server_config = convert_rel_path_to_abs_path(self.__server.get_server_abs_root(),
                                                             ConfigManager.get_config("server_config_cfg_dir"))
        self.__abspath_helper_mod_output = abspath_server_config + "/server_modding_ping.txt"
        self.__lua_engine_no_response_threshold = ConfigManager.get_config("lua_engine_no_response_threshold")
        self.__helper_mod_record_pattern = ConfigManager.get_config("format_helper_mod_record")
        self.__helper_mod_output_invalid_cnt = 0

    def run_server(self):
        Logger.info("NS2 Server Watchdog script.")
        Logger.info("Press Ctrl-C to terminate this script and the running server process.")
        sleep_sec = ConfigManager.get_config("monitor_interval")
        self.__server.start_server()
        while not ExitFlag:
            if self.__is_server_process_missing() or \
                    self.__is_need_daily_restart() or \
                    self.__is_server_lua_engine_dead():
                self.__server.restart_server()
            try:
                time.sleep(sleep_sec)
            except IOError:
                Logger.debug("Main loop met IOError during sleep.")
        self.__server.stop_server()

    def __is_server_process_missing(self):
        PREFIX_STRING = "Process monitor: "
        if self.__server.is_running():
            Logger.debug(PREFIX_STRING + "process alive")
            return False
        else:
            Logger.info(PREFIX_STRING + "unexpected server shutdown detected, restoring...")
            return True

    def __is_need_daily_restart(self):
        if not self.__is_daily_restart_server:
            return False

        PREFIX_STRING = "Daily restart: "
        if time.time() >= self.__next_daily_restart_trigger_time:
            Logger.info(PREFIX_STRING + "now is the time to restart")
            self.__next_daily_restart_trigger_time = self.__calc_next_daily_restart_trigger_timestamp()
            process_info = self.__server.get_info()
            if process_info is not None:
                if process_info["vms"] < self.__daily_restart_vms_threshold:
                    Logger.info(PREFIX_STRING + "server will not get restarted (vms/%d < threshold/%d" % (
                        process_info["vms"], self.__daily_restart_vms_threshold))
                    return False
                else:
                    Logger.info(PREFIX_STRING + "server will get restarted (vms/%d >= threshold/%d)" % (
                        process_info["vms"], self.__daily_restart_vms_threshold))
                    return True
            else:
                Logger.info(PREFIX_STRING + "server will get restarted (server process stopped)")
                return True
        else:  # not now
            return False

    def __is_server_lua_engine_dead(self):
        if not self.__is_check_lua_engine_status:
            return False

        st = "uninitialized"
        is_dead = False
        exception_flag = False
        exception_msg = ""
        PREFIX_STRING = "Lua engine check: "
        try:
            with open(self.__abspath_helper_mod_output, 'r') as f:
                st = f.readline()
            last_update_time = datetime.datetime.strptime(st, self.__helper_mod_record_pattern)
            last_update_timestamp = time.mktime(last_update_time.timetuple())
        except IOError:
            exception_flag = True
            exception_msg = "Fail to open helper mod's output: '%s'." % (
                self.__abspath_helper_mod_output)
        except ValueError:
            exception_flag = True
            exception_msg = "Fail to parse the helper mod's record '%s' with pattern %s." % (
                st, self.__helper_mod_record_pattern)
        except TypeError:
            exception_flag = True
            exception_msg = "Fail to parse the helper mod's record because the file includes invalid character."
        else:
            # successfully parsed the helper mod's record
            self.__helper_mod_output_invalid_cnt = 0
            engine_frozen_time = int(time.time() - last_update_timestamp)
            if engine_frozen_time > self.__lua_engine_no_response_threshold:
                Logger.info(
                    PREFIX_STRING +
                    ("Lua engine has frozen for %d second(s), the server will be restarted" % engine_frozen_time))
                is_dead = True
            else:
                Logger.debug(
                    PREFIX_STRING +
                    ("Lua engine check: OK, frozen_time = %d, threshold = %d" % (
                        engine_frozen_time, self.__lua_engine_no_response_threshold)))
                is_dead = False
        finally:
            if exception_flag:
                # fail to parse the helper mod's record
                self.__helper_mod_output_invalid_cnt = self.__helper_mod_output_invalid_cnt + 1
                if self.__helper_mod_output_invalid_cnt < self.__lua_engine_no_response_threshold:
                    Logger.warn(
                        PREFIX_STRING + exception_msg +
                        (" Assume engine is good (%d/%d)" % (
                            self.__helper_mod_output_invalid_cnt, self.__lua_engine_no_response_threshold)))
                    is_dead = False
                else:
                    Logger.warn(
                        PREFIX_STRING + exception_msg +
                        (" Assume engine is down (%d/%d)" % (
                            self.__helper_mod_output_invalid_cnt, self.__lua_engine_no_response_threshold)))
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
        Logger.info("Captured signal SIGINT, prepare to exit")
        ExitFlag = True


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    Logger.init_logger()

    main(sys.argv)
