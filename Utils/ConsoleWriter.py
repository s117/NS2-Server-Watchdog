# encoding: utf-8
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
