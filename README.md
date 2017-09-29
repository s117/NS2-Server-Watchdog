# NS2-Server-Watchdog
A watchdog script for the NS2 dedicated server. To let the script take care of your server, you should use this script to start your dedicated server.

Tested under Windows.

### Settings in the config.json
        # Monitoring interval in second.
        "monitor_interval": 1,

        # If the server is running, check whether the lua engine is still alive with the help of ping_mod (mod_id=1B2340F1).
        "check_lua_engine_status": True,

        # Lua engine unresponsive tolerance (in seconds).
        # PS:: DO NOT set a too small value, because the record pf ping_mode will stop update during map change and init
        "lua_engine_no_response_threshold": 60,

        # Date format of ping_mod's output.
        "format_ping_mod_record": "%m/%d/%y %H:%M:%S",

        # Dump the memory before restart the unresponsive server.
        "create_mem_dump": False,

        # Whether restart the server every day.
        "daily_restart": True,

        # When to restart the server? (24h, [hh, mm, ss], local time).
        "daily_restart_h_m_s": [04, 00, 00],

        # The server will only get restarted if the memory usage exceeds this threshold
        # (in byte). Set it to 0 if you always want the restart to get triggered.
        "daily_restart_vms_threshold": 768 * 1024 * 1024,

        # NS2Server's root path.
        "server_path": "C:/NS2Server",

        # The name of the server's executable file.
        "server_executable_image": "Server.exe",

        # Path to server config dir.
        "server_config_cfg_dir": "./configs/ns2server_configs",

        # Path to server log dir.
        "server_config_log_dir": "./configs/ns2server_logs",

        # Path to server mod storage dir.
        "server_config_mod_dir": "./configs/ns2server_mods",

        # Additional launch option.
        "server_config_extra_parameter":
            "-name Test -console -port 27015  -map 'ns2_veil' -limit 20 -speclimit 4 -mods '1B2340F1'",

        # Output verbose level, 0 for lowest and 2 for highest.
        "verbose_level": 2
        
MIT Licensed.