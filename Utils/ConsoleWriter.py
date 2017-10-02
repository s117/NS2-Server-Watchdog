# encoding: utf-8
import locale
import sys


class ConsoleWriter:
    @staticmethod
    def encode_text(text):
        return text.encode(locale.getdefaultlocale()[1])

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
