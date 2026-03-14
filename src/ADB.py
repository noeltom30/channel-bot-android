import subprocess
import time

class ADB:
    def __init__(self, adb_path="adb"):
        self.adb_path = adb_path

    def _run(self, args):
        result = subprocess.run(
            [self.adb_path] + args,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() if result.stderr else "Command failed")
        return result.stdout.strip() if result.stdout else ""

    def devices(self):
        return self._run(["devices"])

    def shell(self, cmd):
        return self._run(["shell"] + cmd.split())

    def tap(self, x, y):
        self.shell(f"input tap {x} {y}")

    def text(self, s):
        s = s.replace(" ", "%s")
        self.shell(f"input text {s}")

    def start_app(self, pkg, activity):
        self.shell(f"am start -n {pkg}/{activity}")

    def launch_pkg(self, pkg):
        # monkey-style launch
        self.shell(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1")

    def wait(self, seconds):
        time.sleep(seconds)

    def resolve_activity(self, pkg):
        out = self.shell(f"cmd package resolve-activity --brief {pkg}")
        line = out.strip().splitlines()[-1]
        p, act = line.split("/")
        return p, act

    def ui_dump(self, name="ui.xml"):
        remote = "/sdcard/ui.xml"
        self.shell(f"uiautomator dump {remote}")
        xml = self.shell(f"cat {remote}")
        return xml

    def set_display(self, width, height, density=None):
        self.shell(f"wm size {width}x{height}")
        if density is not None:
            self.shell(f"wm density {density}")

    def scroll(self, pixels=300, x=450, start_y=1190, duration=300):
        end_y = start_y - pixels
        self.shell(f"input swipe {x} {start_y} {x} {end_y} {duration}")