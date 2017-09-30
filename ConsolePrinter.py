# encoding: utf-8
import ctypes

import sys


class ConsoleWriter:
    def init(self):
        pass

    def debug(self, text):
        sys.stdout.write(text)

    def verbose(self, text):
        sys.stdout.write(text)

    def normal(self, text):
        sys.stdout.write(text)

    def warn(self, text):
        sys.stderr.write(text)

    def error(self, text):
        sys.stderr.write(text)


class WindowsConsoleWriter(ConsoleWriter):
    def __init__(self):
        self.init()

    __STD_INPUT_HANDLE = -10
    __STD_OUTPUT_HANDLE = -11
    __STD_ERROR_HANDLE = -12

    __FOREGROUND_BLACK = 0x0
    __FOREGROUND_BLUE = 0x01  # text color contains blue.
    __FOREGROUND_GREEN = 0x02  # text color contains green.
    __FOREGROUND_RED = 0x04  # text color contains red.
    __FOREGROUND_INTENSITY = 0x08  # text color is intensified.

    __BACKGROUND_BLUE = 0x10  # background color contains blue.
    __BACKGROUND_GREEN = 0x20  # background color contains green.
    __BACKGROUND_RED = 0x40  # background color contains red.
    __BACKGROUND_INTENSITY = 0x80  # background color is intensified.

    ''''' See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winprog/winprog/windows_api_reference.asp 
    for information on Windows APIs.'''
    std_out_handle = ctypes.windll.kernel32.GetStdHandle(__STD_OUTPUT_HANDLE)
    std_err_handle = ctypes.windll.kernel32.GetStdHandle(__STD_ERROR_HANDLE)

    @staticmethod
    def set_output_color(color, handle):
        """(color) -> bit 
        Example: set_cmd_color(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY) 
        """
        return ctypes.windll.kernel32.SetConsoleTextAttribute(handle, color)

    def reset_color(self, handle):
        self.set_output_color(
            WindowsConsoleWriter.__FOREGROUND_RED |
            WindowsConsoleWriter.__FOREGROUND_GREEN |
            WindowsConsoleWriter.__FOREGROUND_BLUE,
            handle)

    def init(self):
        self.reset_color(self.std_out_handle)
        self.reset_color(self.std_err_handle)
        pass

    def debug(self, text):
        # dark green
        color = (WindowsConsoleWriter.__FOREGROUND_GREEN |
                 WindowsConsoleWriter.__FOREGROUND_BLUE)

        self.set_output_color(color, self.std_out_handle)
        sys.stdout.write(text)
        self.reset_color(self.std_out_handle)

    def verbose(self, text):
        # bright light green
        color = (WindowsConsoleWriter.__FOREGROUND_GREEN |
                 WindowsConsoleWriter.__FOREGROUND_BLUE |
                 WindowsConsoleWriter.__FOREGROUND_INTENSITY)

        self.set_output_color(color, self.std_out_handle)
        sys.stdout.write(text)
        self.reset_color(self.std_out_handle)

    def normal(self, text):
        # white
        color = (WindowsConsoleWriter.__FOREGROUND_RED |
                 WindowsConsoleWriter.__FOREGROUND_GREEN |
                 WindowsConsoleWriter.__FOREGROUND_BLUE)

        self.set_output_color(color, self.std_out_handle)
        sys.stdout.write(text)
        self.reset_color(self.std_out_handle)

    def warn(self, text):
        # bright yellow
        color = (WindowsConsoleWriter.__FOREGROUND_RED |
                 WindowsConsoleWriter.__FOREGROUND_GREEN |
                 WindowsConsoleWriter.__FOREGROUND_INTENSITY)

        self.set_output_color(color, self.std_err_handle)
        sys.stderr.write(text)
        self.reset_color(self.std_err_handle)

    def error(self, text):
        # bright red
        color = (WindowsConsoleWriter.__FOREGROUND_RED |
                 WindowsConsoleWriter.__FOREGROUND_INTENSITY)

        self.set_output_color(color, self.std_err_handle)
        sys.stderr.write(text)
        self.reset_color(self.std_err_handle)


class UnixConsoleWriter(ConsoleWriter):
    def __init__(self):
        self.init()

    __FOREGROUND_BLACK = 0x0
    __FOREGROUND_BLUE = 0x01  # text color contains blue.
    __FOREGROUND_GREEN = 0x02  # text color contains green.
    __FOREGROUND_RED = 0x04  # text color contains red.
    __FOREGROUND_INTENSITY = 0x08  # text color is intensified.

    __BACKGROUND_BLACK = 0x0
    __BACKGROUND_BLUE = 0x10  # background color contains blue.
    __BACKGROUND_GREEN = 0x20  # background color contains green.
    __BACKGROUND_RED = 0x40  # background color contains red.

    __FG_TABLE = [
        "30", "34", "32", "36", "31", "35", "33", "37"
    ]
    __BG_TABLE = [
        "40", "44", "42", "46", "41", "45", "43", "47"
    ]

    std_out_handle = -11
    std_err_handle = -12

    @staticmethod
    def set_output_color(color, handle):
        bg = (color >> 4) & 0x7
        fg = color & 0x7
        intense = (color >> 3) & 0x1

        esc_seq = "\033[%d;%s;%sm" % (
            intense,
            UnixConsoleWriter.__FG_TABLE[fg],
            UnixConsoleWriter.__BG_TABLE[bg]
        )

        if handle is UnixConsoleWriter.std_out_handle:
            sys.stdout.write(esc_seq)
        else:
            sys.stderr.write(esc_seq)

    @staticmethod
    def reset_color(handle):
        if handle is UnixConsoleWriter.std_out_handle:
            sys.stdout.write('\033[0m')
        else:
            sys.stderr.write('\033[0m')

    def init(self):
        self.reset_color(self.std_out_handle)
        self.reset_color(self.std_err_handle)
        pass

    def debug(self, text):
        # dark green
        color = (UnixConsoleWriter.__FOREGROUND_GREEN |
                 UnixConsoleWriter.__FOREGROUND_BLUE)

        self.set_output_color(color, self.std_out_handle)
        sys.stdout.write(text)
        self.reset_color(self.std_out_handle)

    def verbose(self, text):
        # bright light green
        color = (UnixConsoleWriter.__FOREGROUND_GREEN |
                 UnixConsoleWriter.__FOREGROUND_BLUE |
                 UnixConsoleWriter.__FOREGROUND_INTENSITY)

        self.set_output_color(color, self.std_out_handle)
        sys.stdout.write(text)
        self.reset_color(self.std_out_handle)

    def normal(self, text):
        # white
        color = (UnixConsoleWriter.__FOREGROUND_RED |
                 UnixConsoleWriter.__FOREGROUND_GREEN |
                 UnixConsoleWriter.__FOREGROUND_BLUE)

        self.set_output_color(color, self.std_out_handle)
        sys.stdout.write(text)
        self.reset_color(self.std_out_handle)

    def warn(self, text):
        # bright yellow
        color = (UnixConsoleWriter.__FOREGROUND_RED |
                 UnixConsoleWriter.__FOREGROUND_GREEN |
                 UnixConsoleWriter.__FOREGROUND_INTENSITY)

        self.set_output_color(color, self.std_err_handle)
        sys.stderr.write(text)
        self.reset_color(self.std_err_handle)

    def error(self, text):
        # bright red
        color = (UnixConsoleWriter.__FOREGROUND_RED |
                 UnixConsoleWriter.__FOREGROUND_INTENSITY)

        self.set_output_color(color, self.std_err_handle)
        sys.stderr.write(text)
        self.reset_color(self.std_err_handle)
