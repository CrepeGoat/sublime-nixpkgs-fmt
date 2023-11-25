import sublime
import sublime_plugin

import subprocess

package_name = "nixpkgs-fmt"


class NixpkgsFmtCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # encoding = self.view.encoding()
        settings = sublime.load_settings(package_name + ".sublime-settings")
        fmt_command: list = settings.get("fmt_command")

        full_region = sublime.Region(0, self.view.size())
        original_text = self.view.substr(full_region)

        fmt_result = subprocess.run(
            fmt_command,
            input=original_text,
            capture_output=True,
            text=True,
            check=True,
            # shell=True,
        )

        self.view.replace(
            edit,
            full_region,
            fmt_result.stdout,
        )

    def is_enabled(self):
        syntax_lower = self.view.settings().get("syntax").lower()
        return syntax_lower.endswith("nix.tmlanguage") or syntax_lower.endswith(
            "nix.sublime-syntax"
        )
