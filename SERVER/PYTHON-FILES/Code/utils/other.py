from logging import warning


#
#
# LITTLE BIT OF THIS CODE IN THIS FILE IS IN YOUTUBE-DL.
# Credit to them!
#


# TODO CHANGE TO A BETTER WAY OF TERMINATING TYPE THREAD THING
# Got this somewhere online... and have been edited! Sorry.
def terminate_thread(thread):
    """

    Terminates a python thread from another thread.

    """
    if not thread.isAlive():
        return
    import ctypes
    exc = ctypes.py_object(SystemExit)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(thread.ident), exc)
    if res == 0:
        return [False, "Unable to Terminating Channel Thread, nonexistent thread id"]
    elif res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)
        return [False, "Unable to Terminating Channel Thread, Try again later."]
    return [True, "OK"]


# This gets the best format of the width.
def get_format_from_data(formats, height):
    lower = None
    if type(height) is str:
        if 'original' in height:
            return max(formats, key=lambda x: x['height'])
        else:
            warning("height is a str when it should be a int. Auto getting best format.")
            return max(formats, key=lambda x: x['height'])
    elif type(height) is int:
        for format_ in formats:
            format_height = format_['height']
            if height == format_height:
                return format_
            if format_height < height:
                lower = format_
        return lower
    elif height is None:
        return max(formats, key=lambda x: x['height'])


# This could be changed but as right now, it seems to work.
def get_highest_thumbnail(thumbnails):
    thumbnail_highest = max(thumbnails, key=lambda x: x['width'])
    return str(thumbnail_highest['url'])


def try_get(src, getter, expected_type=None):
    """

    Taken from https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/utils.py#L2312

    """

    if not isinstance(getter, (list, tuple)):
        getter = [getter]
    for get in getter:
        try:
            v = get(src)
        except (AttributeError, KeyError, TypeError, IndexError):
            pass
        else:
            if expected_type is None or isinstance(v, expected_type):
                return v
