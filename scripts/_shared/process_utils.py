"""Bound subprocess trees, including Windows Python -> Docker -> buildx chains."""
import os
import signal
import subprocess


def run_bounded(cmd, *, timeout=120, **kwargs):
    capture = kwargs.pop("capture_output", False)
    if capture:
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data = kwargs.pop("input", None)
    if data is not None:
        kwargs["stdin"] = subprocess.PIPE
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)
    try:
        stdout, stderr = proc.communicate(data, timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        # Killing only the Python wrapper leaves buildx holding the output pipes.
        if os.name == "nt":
            try:
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                pass
        else:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if proc.poll() is None:
            proc.kill()
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            for stream in (proc.stdout, proc.stderr, proc.stdin):
                if stream:
                    stream.close()
        raise
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
