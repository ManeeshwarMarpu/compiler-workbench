
import bdb, sys, types

class LineStepper(bdb.Bdb):
    def __init__(self):
        super().__init__()
        self.events = []  # list of (event, filename, lineno, locals)

    def user_line(self, frame):
        code = frame.f_code
        filename = code.co_filename
        lineno = frame.f_lineno
        locs = dict(frame.f_locals)
        self.events.append(("line", filename, lineno, {k: repr(v) for k,v in locs.items()}))
        self.set_step()

    def run_script(self, src: str):
        # Run in its own global dict so 'print' works
        glb = {"__name__": "__main__"}
        self.reset()
        self.set_step()
        try:
            self.runctx(src, glb, glb)
        except SystemExit:
            pass
        except BaseException as e:
            self.events.append(("exception", "<stdin>", -1, {"error": repr(e)}))
        return self.events
