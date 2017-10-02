# encoding: utf-8
import ctypes
import sys

from ConsoleWriter import ConsoleWriter


class WindowsConsoleWriter(ConsoleWriter):
    def __init__(self):
        self.reset_color(self.std_out_handle)
        self.reset_color(self.std_err_handle)

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
        # bright white
        color = (WindowsConsoleWriter.__FOREGROUND_RED |
                 WindowsConsoleWriter.__FOREGROUND_GREEN |
                 WindowsConsoleWriter.__FOREGROUND_BLUE |
                 WindowsConsoleWriter.__FOREGROUND_INTENSITY)

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
