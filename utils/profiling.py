import datetime
import logging
import os
import psutil
import platform

class Profiling(object):
    _EN_LOGGING = False
    _EN_STATS = True
    _EN_MEM_STATS = False
    _LOGGER = logging.getLogger("profiling")

    _function_dict = {}
    @classmethod
    def enable_call_logging(cls):
        cls._EN_LOGGING = True

    @classmethod
    def enable_stats(cls):
        cls._EN_STATS = True

    @classmethod
    def enable_memory(cls):
        cls.enable_call_logging()
        cls._EN_MEM_STATS = True

    @classmethod
    def clear_stats(cls):
        cls._function_dict = {}

    @classmethod
    def get_funcs(cls):
        ret = []
        for i in cls._function_dict:
            ret.append(i)
        return ret

    @classmethod
    def profile_function(cls, func):
        """Decorator to measure execution wall time"""
        def inner(*args, **kwargs):

            if cls._EN_STATS or cls._EN_LOGGING:
                if cls._EN_MEM_STATS:
                    process = psutil.Process(os.getpid())
                    mi = process.memory_info()
                    # mi.rss, mi.vms, mi.shared
                start = datetime.datetime.now()
                ret = func(*args, **kwargs)
                delta = datetime.datetime.now() - start
                if cls._EN_MEM_STATS:
                    process = psutil.Process(os.getpid())
                    mif = process.memory_info()
                    if platform.system() == 'Windows':
                        md = [mif.rss - mi.rss, mif.vms - mi.vms, 0]
                    else:
                        md = [mif.rss - mi.rss,mif.vms - mi.vms,mif.shared - mi.shared]

                name = func.__module__ + "." + func.__name__
                if cls._EN_STATS:
                    fstat = cls._function_dict.get(name)
                    if fstat is None:
                        cls._function_dict[name] = [1, delta]
                    else:
                        cls._function_dict[name] = [fstat[0] + 1, fstat[1] + delta]

                if cls._EN_LOGGING:
                    meminfo = ""
                    if cls._EN_MEM_STATS:
                        meminfo = "rss vms shared {} {} {}".format(cls.format_mem(md[0]), cls.format_mem(md[1]), cls.format_mem(md[2]))
                    cls._LOGGER.debug("{} took {} {}".format(name, delta, meminfo))
            else:
                ret = func(*args, **kwargs)
            return ret
        return inner
    @classmethod
    def format_mem(cls, b):

        if abs(b) < 1024:
            return str(b) + "B"
        if abs(b) < (1024*1024):
            return str(b/1024) + "kB"
        return str(b/1024/1024) + "MB"



    @classmethod
    def print_profile(cls):
        for i in cls._function_dict:
            cls._LOGGER.info("{} called {} times and took {}".format(i, cls._function_dict[i][0], cls._function_dict[i][1]))
