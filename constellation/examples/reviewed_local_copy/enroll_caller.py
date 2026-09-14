#!/usr/bin/env python3
"""Pin an explicitly supplied native deployment; never provision or execute it."""
import argparse
import hashlib
import os
from pathlib import Path
import stat

from prepare_review_candidate import canonical, read
from reviewed_action import INPUTS, PROGRAMS, configuration, pinned, require


def enroll(layout):
    require(set(layout['programs']) == PROGRAMS and set(layout['inputs']) == INPUTS,
        'every native program/input must be explicitly located')
    result = dict(layout)
    for group in ('programs', 'inputs'):
        result[group] = {}
        for name, locator in layout[group].items():
            path = Path(locator)
            require(path.is_absolute(), 'absolute native locator required')
            maximum = ((1024 if name == 'app_server' else 256) * 1024**2
                if group == 'programs' else 16 * 1024**2)
            # Do not read backend credential files or copy CLI home/configuration.
            # These are the caller-selected program and protocol document bytes.
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            with os.fdopen(fd, 'rb') as stream:
                status = os.fstat(stream.fileno())
                require(stat.S_ISREG(status.st_mode) and 0 < status.st_size <= maximum, 'native input type/size refused')
                identity = 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()
            entry = {'path': str(path), 'sha256': identity}
            pinned(entry, maximum)
            result[group][name] = entry
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    config = enroll(read(args.layout)[0])
    with args.output.open('xb') as stream:
        stream.write(canonical(config)); stream.flush(); os.fsync(stream.fileno())
    configuration(args.output)
    print('Native locators pinned and enrollment cross-checked; no native command invoked.')


if __name__ == '__main__': main()

