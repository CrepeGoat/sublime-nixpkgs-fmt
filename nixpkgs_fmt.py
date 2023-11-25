import sublime
import sublime_plugin

import subprocess

package_name = "nixpkgs-fmt"


class NixpkgsFmtCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # encoding = self.view.encoding()
        package_settings = sublime.load_settings(package_name + ".sublime-settings")
        fmt_command: list = package_settings.get("fmt_command")

        full_region = sublime.Region(0, self.view.size())
        original_text = self.view.substr(full_region)
        if len(original_text) == 0:
            return

        fmt_result = subprocess.run(
            fmt_command,
            input=original_text,
            capture_output=True,
            text=True,
            check=True,
            # shell=True,
        )
        if fmt_result.stdout == original_text:
            return

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


class NixpkgsFmtOnSaveEventListener(sublime_plugin.ViewEventListener):
    def is_applicable(settings):
        syntax_lower = settings.get("syntax").lower()
        is_applicable_syntax = syntax_lower.endswith(
            "nix.tmlanguage"
        ) or syntax_lower.endswith("nix.sublime-syntax")

        package_settings = sublime.load_settings(package_name + ".sublime-settings")
        return package_settings.get("trigger_on_save") and is_applicable_syntax

    def applies_to_primary_view_only():
        return True

    def on_pre_save(self):
        self.view.run_command("nixpkgs_fmt")
