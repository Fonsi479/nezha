#!/usr/bin/env python3
"""Open the private dashboard through a task-owned SSH forwarding process."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request
import webbrowser

PRIVATE = Path.home() / 'Library/Application Support/Codex/Nezha'


def ready(url, site_name):
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url + '/api/v1/setting', timeout=10) as response:
            data = json.load(response)
        return data.get('success') is True and data.get('data', {}).get('config', {}).get('site_name') == site_name
    except (OSError, ValueError, urllib.error.URLError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--settings', type=Path, default=PRIVATE / 'access.json')
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args()
    settings = json.loads(args.settings.read_text())
    port = int(settings.get('local_port', 18765))
    if not 1024 <= port <= 65535:
        parser.error('local_port must be between 1024 and 65535')
    url = f'http://127.0.0.1:{port}'
    if not ready(url, settings['site_name']):
        env = dict(os.environ, **settings.get('ssh_env', {}))
        command = ['ssh', '-C', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=15',
                   '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=30',
                   '-o', 'ServerAliveCountMax=3', '-N', '-L',
                   f'127.0.0.1:{port}:127.0.0.1:8008', *settings['ssh_args']]
        log = PRIVATE / 'tunnel.log'
        log.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with log.open('ab') as output:
            log.chmod(0o600)
            child = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL,
                                     stdout=output, stderr=output, start_new_session=True)
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise RuntimeError(f'SSH tunnel failed; see {log}')
                if ready(url, settings['site_name']):
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError(f'Dashboard connection timed out; see {log}')
        except BaseException:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
            raise
    print(url)
    if not args.no_open:
        webbrowser.open(url)


if __name__ == '__main__':
    main()
