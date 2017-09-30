# encoding: utf-8
import sys

from ConsoleWriter import ConsoleWriter


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
        # bright white
        color = (UnixConsoleWriter.__FOREGROUND_RED |
                 UnixConsoleWriter.__FOREGROUND_GREEN |
                 UnixConsoleWriter.__FOREGROUND_BLUE |
                 UnixConsoleWriter.__FOREGROUND_INTENSITY)

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
