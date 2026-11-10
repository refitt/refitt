"""Report what a command run by a throwaway helper sees, as JSON.

Run as the helper's command: `uv run python -I config_probe.py OUT.json`.
It records the process's view (cwd, HOME, TMPDIR, REPO_ROOT, PGTZ, the
exported rootkey), REFITT's loaded configuration with its system, user and
local file layers, and what the configured database holds. On Postgres it
also records the session time zone of a libpq connection.

VHH_PROBE_NO_DB=1 skips the database (a stubbed bring-up has none);
VHH_PROBE_HTTP=1 records whether the configured API site answers HTTP.
"""

import json
import os
import sys


def plain(value):
    """Namespaces and other mappings as plain dicts, recursively."""
    if hasattr(value, 'items'):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def main(out: str) -> None:
    report = {
        'cwd': os.path.realpath(os.getcwd()),
        'home': os.path.realpath(os.environ.get('HOME', '')),
        'tmpdir': os.path.realpath(os.environ.get('TMPDIR', '')),
        'repo_root': os.environ.get('REPO_ROOT'),
        'pgtz': os.environ.get('PGTZ'),
        'env_rootkey': os.environ.get('REFITT_API_ROOTKEY'),
        'uv_no_sync': os.environ.get('UV_NO_SYNC'),
    }
    from refitt.core.config import config
    report['layers'] = {name: plain(config.namespaces.get(name, {}))
                        for name in ('system', 'user', 'local')}
    report['database'] = plain(config.database.default)
    report['rootkey'] = plain(config.api.get('rootkey'))
    from cryptography.fernet import Fernet
    try:
        Fernet(report['rootkey'])
        report['rootkey_valid'] = True
    except Exception:  # noqa: BLE001 - any failure means not a Fernet key
        report['rootkey_valid'] = False
    report['api_site'] = plain(config.api.get('site'))
    report['api_port'] = plain(config.api.get('port'))
    if os.environ.get('VHH_PROBE_HTTP') == '1':
        import urllib.error
        import urllib.request
        url = f"{config.api.site}:{config.api.port}/"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            opener.open(url, timeout=5)
            report['server_answered'] = True
        except urllib.error.HTTPError:
            report['server_answered'] = True
        except OSError:
            report['server_answered'] = False
    db = config.database.default
    if os.environ.get('VHH_PROBE_NO_DB') == '1':
        pass
    elif db.provider == 'sqlite':
        import sqlite3
        with sqlite3.connect(db.file) as conn:
            report['users'] = conn.execute('SELECT count(*) FROM user').fetchone()[0]
    else:
        import psycopg2
        conn = psycopg2.connect(host=db.host, port=db.port, dbname=db.database,
                                user=db.user, password=db.password, connect_timeout=5)
        try:
            cur = conn.cursor()
            cur.execute('SHOW timezone')
            report['session_timezone'] = cur.fetchone()[0]
            cur.execute('SELECT count(*) FROM "user"')
            report['users'] = cur.fetchone()[0]
        finally:
            conn.close()
    with open(out, 'w') as stream:
        json.dump(report, stream, indent=1, sort_keys=True)


if __name__ == '__main__':
    main(sys.argv[1])
