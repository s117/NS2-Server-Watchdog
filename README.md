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
            "-name 'Test' -console -port 27015  -map 'ns2_veil' -limit 20 -speclimit 4 -mods '44AE3979'",

        # Output verbose level, 0 for lowest and 2 for highest.
        "verbose_level": 2

Tested under Windows & Linux / Python 2.7.13 / NS2DS build317

MIT License.
