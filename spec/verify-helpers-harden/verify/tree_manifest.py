"""Print a manifest of a directory tree: every entry, its type, mode and content hash.

Two manifests of the same tree compare equal only if no file, directory or
link was added, removed, retyped, re-moded or changed in content.
Usage: python -I tree_manifest.py DIR
"""

import hashlib
import os
import stat
import sys


def main(root: str) -> None:
    rows = []
    for top, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(dirs + files):
            full = os.path.join(top, name)
            rel = os.path.relpath(full, root)
            st = os.lstat(full)
            mode = stat.S_IMODE(st.st_mode)
            if stat.S_ISLNK(st.st_mode):
                rows.append(f'l {mode:o} {os.readlink(full)} {rel}')
            elif stat.S_ISDIR(st.st_mode):
                rows.append(f'd {mode:o} - {rel}')
            elif stat.S_ISREG(st.st_mode):
                with open(full, 'rb') as stream:
                    digest = hashlib.sha256(stream.read()).hexdigest()
                rows.append(f'f {mode:o} {digest} {rel}')
            else:  # a FIFO, socket or device: never opened
                rows.append(f's {mode:o} - {rel}')
    print('\n'.join(rows))


if __name__ == '__main__':
    main(sys.argv[1])
