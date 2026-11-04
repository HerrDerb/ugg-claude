"""The only place that knows about the OS: locks, detached processes, executable lookup."""
import os
import shutil

if os.name == "nt":
    import msvcrt
else:
    import fcntl


def exe(name):
    """Full path of a tool. On Windows npm installs `claude.cmd`, which a plain list call cannot find."""
    return shutil.which(name) or name


def detach_kwargs(os_name=os.name):
    """Popen arguments for a child that outlives us and has no console window."""
    if os_name == "nt":
        DETACHED_PROCESS, CREATE_NEW_PROCESS_GROUP, CREATE_NO_WINDOW = 0x8, 0x200, 0x08000000
        return {"creationflags": DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW}
    return {"start_new_session": True}


def try_lock(path):
    """Exclusive non-blocking lock. Returns a handle to pass to unlock(), or None if held elsewhere."""
    f = open(path, "a+")
    try:
        if os.name == "nt":
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except OSError:
        f.close()
        return None


def unlock(handle):
    try:
        if os.name == "nt":
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(handle, fcntl.LOCK_UN)
    finally:
        handle.close()


def is_locked(path):
    if not os.path.exists(path):
        return False
    held = try_lock(path)
    if held is None:
        return True
    unlock(held)
    return False
