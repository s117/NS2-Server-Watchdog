# NS2-Server-Watchdog
A watchdog script (Python 2.7) for the NS2 dedicated server. It can help the server admin to:

1. Daily restart the server according to the memory leaking status
2. Auto restart the unexpected crashed server
3. Auto restart the (Lua VM) frozen server
4. Auto restart the server if it get stuck on downloading mod from Steam

* 3 & 4 requires the server install this [helper mod](http://steamcommunity.com/sharedfiles/filedetails/?id=1152268665) to detect the status of lua VM (Server VM)

To let the script take care of your server, you should use this script to start your dedicated server.

### Settings in the config.json (UTF-8 encoding)
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
        # NS2Server's root path, the script will automatic choose binary from x86 or x64 folder
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

Tested under Windows & Linux / Python 2.7.13 / NS2DS build325

MIT License.
