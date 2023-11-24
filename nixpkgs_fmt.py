import sublime
import sublime_plugin
import subprocess as sub
import os
import sys
from . import difflib

SETTINGS = 'nixpkgs-fmt.sublime-settings'
DICT_KEY = 'nixpkgs-fmt'
IS_WINDOWS = os.name == 'nt'


def is_nix_view(view):
    return view.score_selector(0, 'source.nix') > 0


def get_setting(view, key):
    global_overrides = view.settings().get(DICT_KEY)
    if isinstance(global_overrides, dict) and key in global_overrides:
        return global_overrides[key]
    return sublime.load_settings(SETTINGS).get(key)


def get_env(view):
    val = get_setting(view, 'env')
    if val is None:
        return None
    env = os.environ.copy()
    env.update(val)
    return env


# Copied from other plugins, haven't personally tested on Windows
def process_startup_info():
    if not IS_WINDOWS:
        return None
    startupinfo = sub.STARTUPINFO()
    startupinfo.dwFlags |= sub.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = sub.SW_HIDE
    return startupinfo


def guess_cwd(view):
    mode = get_setting(view, 'cwd_mode')

    if mode.startswith(':'):
        return mode[1:]

    if mode == 'none':
        return None

    if mode == 'project_root':
        if len(view.window().folders()):
            return view.window().folders()[0]
        return None

    if mode == 'auto':
        if view.file_name():
            return os.path.dirname(view.file_name())
        elif len(view.window().folders()):
            return view.window().folders()[0]


def merge_into_view(view, edit, new_src):
    def subview(start, end):
        return view.substr(sublime.Region(start, end))
    diffs = difflib.myers_diffs(subview(0, view.size()), new_src)
    difflib.cleanup_efficiency(diffs)
    merged_len = 0
    for (op_type, patch) in diffs:
        patch_len = len(patch)
        if op_type == difflib.Ops.EQUAL:
            if subview(merged_len, merged_len+patch_len) != patch:
                raise Exception("[sublime-nixpkgs-fmt] mismatch between diff's source and current content")
            merged_len += patch_len
        elif op_type == difflib.Ops.INSERT:
            view.insert(edit, merged_len, patch)
            merged_len += patch_len
        elif op_type == difflib.Ops.DELETE:
            if subview(merged_len, merged_len+patch_len) != patch:
                raise Exception("[sublime-nixpkgs-fmt] mismatch between diff's source and current content")
            view.erase(edit, sublime.Region(merged_len, merged_len+patch_len))


def run_format(view, input, encoding):
    exec = get_setting(view, 'executable')
    args = exec if isinstance(exec, list) else [exec]

    proc = sub.Popen(
        args=args,
        stdin=sub.PIPE,
        stdout=sub.PIPE,
        stderr=sub.PIPE,
        startupinfo=process_startup_info(),
        universal_newlines=False,
        cwd=guess_cwd(view),
        env=get_env(view),
    )

    (stdout, stderr) = proc.communicate(input=bytes(input, encoding=encoding))
    (stdout, stderr) = stdout.decode(encoding), stderr.decode(encoding)

    if proc.returncode != 0:
        err = sub.CalledProcessError(proc.returncode, args)

        if get_setting(view, 'error_messages'):
            msg = str(err)
            if len(stderr) > 0:
                msg += ':\n' + stderr
            msg += '\nNote: to disable error popups, set the nixpkgs-fmt setting "error_messages" to false.'
            sublime.error_message(msg)

        raise err

    if len(stderr) > 0:
        print('[sublime-nixpkgs-fmt]:', stderr, file=sys.stderr)

    return stdout


def view_encoding(view):
    encoding = view.encoding()
    return 'UTF-8' if encoding == 'Undefined' else encoding


class nixpkgs_fmt_format_buffer(sublime_plugin.TextCommand):
    def is_enabled(self):
        return is_nix_view(self.view)

    def run(self, edit):
        view = self.view
        content = view.substr(sublime.Region(0, view.size()))

        stdout = run_format(
            view=view,
            input=content,
            encoding=view_encoding(view),
        )

        merge_type = get_setting(view, 'merge_type')

        if merge_type == 'diff':
            merge_into_view(view, edit, stdout)

        elif merge_type == 'replace':
            position = view.viewport_position()
            view.replace(edit, sublime.Region(0, view.size()), stdout)
            # Works only on main thread, hence lambda and timer.
            restore = lambda: view.set_viewport_position(position, animate=False)
            sublime.set_timeout(restore, 0)

        else:
            raise Exception('[sublime-nixpkgs-fmt] unknown merge_type setting: {}'.format(merge_type))


class nixpkgs_fmt_listener(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        if is_nix_view(view) and get_setting(view, 'format_on_save'):
            view.run_command('nixpkgs_fmt_format_buffer')
