# encoding: utf-8
import locale
import sys

default_locale = locale.getdefaultlocale()[1]


class ConsoleWriter:
    def __init__(self):
        pass

    @staticmethod
    def encode_text(text):
        if isinstance(text, unicode):
            text = text.encode(default_locale)
        elif not isinstance(text, str):
            raise TypeError("text should be either unicode or str")
        return text

    def debug(self, text):
        text = self.encode_text(text)
        sys.stdout.write(text)

    def verbose(self, text):
        text = self.encode_text(text)
        sys.stdout.write(text)

    def normal(self, text):
        text = self.encode_text(text)
        sys.stdout.write(text)

    def warn(self, text):
        text = self.encode_text(text)
        sys.stderr.write(text)

    def error(self, text):
        text = self.encode_text(text)
        sys.stderr.write(text)
