import sublime
import sublime_plugin


class NixpkgsFmtCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        print("it's running!")
