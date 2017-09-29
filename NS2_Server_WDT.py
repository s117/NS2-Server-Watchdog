# -*- encoding:UTF-8 -*-
import datetime
import json
import os
import shlex
import signal
import sys
import time
from subprocess import Popen, CREATE_NEW_CONSOLE

import psutil

VERBOSE_LEVEL = 0
ExitFlag = False


class Logger:
    __TIME_LABEL_PATTERN = '%Y-%m-%d %H:%M:%S'

    def __init__(self):
        raise NotImplementedError("This class should never be instantiated.")

    @staticmethod
    def debug(text):
        if VERBOSE_LEVEL >= 2:
            print time.strftime(Logger.__TIME_LABEL_PATTERN, time.localtime(time.time())) + " [DEBUG]   - " + str(text)

    @staticmethod
    def verbose(text):
        if VERBOSE_LEVEL >= 1:
            print time.strftime(Logger.__TIME_LABEL_PATTERN, time.localtime(time.time())) + " [VERBOSE] - " + str(text)

    @staticmethod
    def info(text):
        print time.strftime(Logger.__TIME_LABEL_PATTERN, time.localtime(time.time())) + " [INFO]    - " + str(text)

    @staticmethod
    def warn(text):
        print time.strftime(Logger.__TIME_LABEL_PATTERN, time.localtime(time.time())) + " [WARN]    - " + str(text)

    @staticmethod
    def fatal(text, exitcode=-1):
        print time.strftime(Logger.__TIME_LABEL_PATTERN, time.localtime(time.time())) + " [FATAL]   - " + str(text)
        print time.strftime(Logger.__TIME_LABEL_PATTERN, time.localtime(
            time.time())) + " [FATAL]   - " + "Program terminated, exit code: %d." % exitcode
        exit(exitcode)


class ConfigManager:
    _manager = None
    _CONFIG_FILENAME = "config.json"
    _DEFAULT_CONFIG = {
        # Monitoring interval in second.
        "monitor_interval": 1,

        # If the server is running, check is the lua engine still alive with the help of ping_mod(id=1B2340F1).
        "check_lua_engine_status": True,

        # Lua engine unresponsive tolerance (in seconds)
        # PS:: DO NOT set a too small value, because the record pf ping_mode will stop update during map change and init
        "lua_engine_no_response_threshold": 60,

        # Date format of ping_mod's output
        "format_ping_mod_record": "%m/%d/%y %H:%M:%S",

        # Dump the memory before restart the unresponsive server.
        "create_mem_dump": False,

        # Whether restart the server everyday.
        "daily_restart": True,

        # When to restart the server? (24h, [hh, mm, ss], local time)
        "daily_restart_h_m_s": [04, 00, 00],

        # The server will only get restarted if the memory usage exceed this threshold
        # (in byte). Set it to 0 if you always want the restart get triggered.
        "daily_restart_vms_threshold": 768 * 1024 * 1024,

        # NS2Server's root path.
        "server_path": "C:/NS2Server",
        # The name of the Server's executable file
        "server_executable_image": "Server.exe",
        # Path to server config dir
        "server_config_cfg_dir": "./configs/ns2server_configs",
        # Path to server log dir
        "server_config_log_dir": "./configs/ns2server_logs",
        # Path to server mod storage dir
        "server_config_mod_dir": "./configs/ns2server_mods",
        # Additional launch option
        "server_config_extra_parameter":
            "-name Test -console -port 27015  -map 'ns2_veil' -limit 20 -speclimit 4 -mods '1B2340F1'",
        # Output verbose level, 0 for lowest and 2 for highest
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
        with open(ConfigManager._CONFIG_FILENAME, 'w') as f:
            f.write(json.dumps(ConfigManager.__config, indent=4, sort_keys=True))
        Logger.info("Flushed config to '%s'" % ConfigManager._CONFIG_FILENAME)

    @staticmethod
    def load_config():
        ConfigManager.__config = {}
        if os.path.exists(ConfigManager._CONFIG_FILENAME):
            Logger.info("Loading config from file '%s'" % ConfigManager._CONFIG_FILENAME)
            with open(ConfigManager._CONFIG_FILENAME) as json_file:
                json_data = json.load(json_file)
                for i, v in ConfigManager._DEFAULT_CONFIG.items():
                    if i in json_data:
                        ConfigManager.__config[i] = json_data[i]
                    else:
                        ConfigManager.__config[i] = ConfigManager._DEFAULT_CONFIG[i]
        else:
            Logger.info("File '%s' not found, a new one will be created" % ConfigManager._CONFIG_FILENAME)
            ConfigManager.__config = ConfigManager._DEFAULT_CONFIG
        ConfigManager.save_config()
        Logger.info("Config loaded")


class ServerProcessHandler:
    __WAIT_TIME_BEFORE_FORCE_KILL = 5
    __WAIT_TIME_BEFORE_GIVE_UP = 5

    def __init__(self):
        if not os.path.isdir(ConfigManager.get_config("server_path")):
            Logger.fatal("The root of NS2Server ('%s') does not exist" % ConfigManager.get_config("server_path"))

        prev_dir = os.getcwd()
        os.chdir(ConfigManager.get_config("server_path"))

        param = []
        key_dir = ["server_config_cfg_dir", "server_config_log_dir", "server_config_mod_dir"]
        for kd in key_dir:
            vd = ConfigManager.get_config(kd)
            if not os.path.isdir(vd):
                Logger.fatal(
                    "Fail to start server, because directory '%s' does not exist (value of config '%s')" % (vd, kd))
            if not os.path.isabs(vd):
                Logger.warn("You are using relative path '%s' for config '%s')" % (vd, kd))
        executable_path = ConfigManager.get_config("server_path") + "/" + ConfigManager.get_config(
            "server_executable_image")
        if not os.path.isfile(executable_path):
            Logger.fatal("Fail to start server, because executable file '%s' does not exist" % executable_path)

        param.append(executable_path)

        param.append("-config_path")
        param.append("" + ConfigManager.get_config("server_config_cfg_dir") + "")

        param.append("-modstorage")
        param.append("" + ConfigManager.get_config("server_config_mod_dir") + "")

        param.append("-logdir")
        param.append("" + ConfigManager.get_config("server_config_log_dir") + "")

        self.__param = param + shlex.split(ConfigManager.get_config("server_config_extra_parameter"))

        self.__pid = -1
        self.__process = None
        self.__ps = None
        self.__ps_cmdline = None
        self.__ps_create_time = 0.0

        os.chdir(prev_dir)

    def restart_server(self):
        self.stop_server()
        self.start_server()

    def start_server(self):
        self.__force_update_ping_mode_data()
        if not self.is_running():
            self.__archive_log_and_dmp()

            prev_dir = os.getcwd()
            os.chdir(ConfigManager.get_config("server_path"))

            try:
                cmdline = ""
                for p in self.__param:
                    cmdline = cmdline + p + " "

                self.__process = Popen(cmdline,
                                       cwd=ConfigManager.get_config("server_path"),
                                       creationflags=CREATE_NEW_CONSOLE)

                self.__pid = self.__process.pid
                self.__ps = psutil.Process(pid=self.__pid)
                self.__ps_cmdline = ""

                for i in self.__ps.cmdline():
                    self.__ps_cmdline = self.__ps_cmdline + i + " "
                self.__ps_create_time = self.__ps.create_time()

            except psutil.NoSuchProcess:
                self.__pid = -1
                self.__process = None
                self.__ps = None
                self.__ps_cmdline = None
                Logger.fatal("Fail to start the server, please check the setting and the server's integrity")
            except psutil.AccessDenied:
                Logger.fatal("Access denied when try to control the server process (pid %d)" % self.__pid)

            os.chdir(prev_dir)

    def stop_server(self):
        if self.is_running():
            try:
                Logger.info("Try to stop server process (pid %d) by terminate()" % self.__pid)
                self.__ps.terminate()
                try:
                    self.__ps.wait(15)
                    Logger.info("Server process (pid %d) get terminated" % self.__pid)
                except psutil.TimeoutExpired:
                    Logger.warn("Fail to stop server process (pid %d) by terminate(), trying kill()" % self.__pid)
                    try:
                        self.__ps.kill()
                        self.__ps.wait(15)
                        Logger.info("Server process (pid %d) get killed" % self.__pid)
                    except psutil.TimeoutExpired:
                        Logger.fatal("Fail to terminate server process (pid %d)" % self.__pid)

            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                Logger.fatal("Access denied when try to control the server process (pid %d)" % self.__pid)

            Logger.info("Stop server process (pid %d) successfully" % self.__pid)

            self.__pid = -1
            self.__process = None
            self.__ps = None
            self.__ps_cmdline = None

            self.__archive_log_and_dmp()

    def is_running(self):
        try:
            if (self.__pid is not -1) and \
                    (self.__process.poll() is None) and \
                    (cmp(self.__ps.status(), "running") is 0):
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

    def __force_update_ping_mode_data(self):
        # The ping_mode's record need to be removed before start because otherwise
        # the launching progress will be disturbed by the lua engine check.
        DEFAULT_PING_MODE_NAME = "server_modding_ping.txt"
        ABS_SERVER_CONFIG_DIR = convert_rel_path_to_abs_path(ConfigManager.get_config("server_path"),
                                                             ConfigManager.get_config("server_config_cfg_dir"))
        ABS_PATH_PING_MODE_TXT = ABS_SERVER_CONFIG_DIR + "/" + DEFAULT_PING_MODE_NAME
        try:
            expire_time = time.time() + ConfigManager.get_config("lua_engine_no_response_threshold")

            st = time.strftime(ConfigManager.get_config("format_ping_mod_record"), time.localtime(expire_time))
            with open(ABS_PATH_PING_MODE_TXT, 'w') as f:
                f.write(st)
        except IOError:
            Logger.fatal("Fail to force update the ping_mode record, check user permission")
        else:
            Logger.verbose("Force updated the ping_mod record, value: %s")

    def __archive_log_and_dmp(self):
        DEFAULT_LOG_FILE_NAME = "log-Server.txt"
        DEFAULT_DUMP_FILE_NAME = "lastcrash.dmp"

        time_label = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(time.time()))

        prev_dir = os.getcwd()
        os.chdir(ConfigManager.get_config("server_path"))
        os.chdir(ConfigManager.get_config("server_config_log_dir"))

        try:
            if os.path.exists(DEFAULT_DUMP_FILE_NAME):
                Logger.verbose("Archived the crash dump: '%s' -> '%s'" % (
                    DEFAULT_DUMP_FILE_NAME, time_label + "_" + DEFAULT_DUMP_FILE_NAME))
                os.rename(DEFAULT_DUMP_FILE_NAME, time_label + "_" + DEFAULT_DUMP_FILE_NAME)
        except Exception:
            Logger.fatal("Fail to archive the crash dump file. (Maybe the last server process is still running?)")

        try:
            if os.path.exists(DEFAULT_LOG_FILE_NAME):
                Logger.verbose("Archived the server log: '%s' -> '%s'" % (
                    DEFAULT_LOG_FILE_NAME, time_label + "_" + DEFAULT_LOG_FILE_NAME))
                os.rename(DEFAULT_LOG_FILE_NAME, time_label + "_" + DEFAULT_LOG_FILE_NAME)
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
        abspath_server_config = convert_rel_path_to_abs_path(ConfigManager.get_config("server_path"),
                                                             ConfigManager.get_config("server_config_cfg_dir"))
        self.__abspath_ping_mod_output = abspath_server_config + "/server_modding_ping.txt"
        self.__lua_engine_no_response_threshold = ConfigManager.get_config("lua_engine_no_response_threshold")

    def run_server(self):
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
        if self.__server.is_running():
            Logger.debug("Process monitor: process alive")
            return False
        else:
            Logger.info("Process monitor: unexpected server shutdown detected, restoring...")
            return True

    def __is_need_daily_restart(self):
        if not self.__is_daily_restart_server:
            return False

        if time.time() >= self.__next_daily_restart_trigger_time:
            Logger.info("Daily restart: Now is the time to restart")
            self.__next_daily_restart_trigger_time = self.__calc_next_daily_restart_trigger_timestamp()
            process_info = self.__server.get_info()
            if process_info is not None:
                if process_info["vms"] < self.__daily_restart_vms_threshold:
                    Logger.info("Daily restart: server will not get restarted (vms/%d < threshold/%d" % (
                        process_info["vms"], self.__daily_restart_vms_threshold))
                    return False
                else:
                    Logger.info("Daily restart: server will get restarted (vms/%d >= threshold/%d)" % (
                        process_info["vms"], self.__daily_restart_vms_threshold))
                    return True
            else:  # not now
                Logger.info("Daily restart: server will get restarted (server process stopped)")
                return True
        else:
            return False

    def __is_server_lua_engine_dead(self):
        if not self.__is_check_lua_engine_status:
            return False

        if not os.path.isfile(self.__abspath_ping_mod_output):
            Logger.warn(
                "Lua engine check: Fail to find ping_mod's output at '%s'. Assume engine is well" % (
                    self.__abspath_ping_mod_output))
            return False

        st = "uninitialized"
        try:
            with open(self.__abspath_ping_mod_output, 'r') as f:
                st = f.readline()
                last_update_time = datetime.datetime.strptime(st, ConfigManager.get_config("format_ping_mod_record"))
                last_update_timestamp = time.mktime(last_update_time.timetuple())
        except IOError:
            Logger.warn(
                "Lua engine check: Fail to open ping_mod's output '%s'. Assume engine is good" % (
                    self.__abspath_ping_mod_output))
            return False
        except ValueError:
            Logger.warn(
                "Lua engine check: Fail to parse the %s with pattern %s in ping_mod's record. Assume engine is down" % (
                    st, ConfigManager.get_config("format_ping_mod_record")))
            return True
        else:
            engine_frozen_time = int(time.time() - last_update_timestamp)
            if engine_frozen_time > self.__lua_engine_no_response_threshold:
                Logger.info(
                    "Lua engine check: Lua engine has frozen for %d second(s), the server will be restarted" % (
                        engine_frozen_time))
                return True
            else:
                Logger.debug(
                    "Lua engine check: OK, frozen_time = %d, threshold = %d" % (
                        engine_frozen_time, self.__lua_engine_no_response_threshold))
                return False

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
    VERBOSE_LEVEL = ConfigManager.get_config("verbose_level")
    main(sys.argv)
