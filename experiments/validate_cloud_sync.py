#!/usr/bin/env python3
"""Physical check of home Wi-Fi sync on the connected board.

1. optional USB provisioning of the site URL + credentials (never printed);
2. wait until the board reports it is at home and idle;
3. simulate an outing by turning Wi-Fi off (serial O) and let it record;
4. turn Wi-Fi back on (serial W): the board must close the session by itself;
5. download that session over the LAN, hash it, and poll the website's
   device endpoint until it confirms the same SHA-256.

Configuration stays in an ignored local JSON: {"port","url","bypass","token"}.
Requires pyserial and requests. Never deletes recordings.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import requests
import serial


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--provision', action='store_true')
    p.add_argument('--seconds', type=int, default=70, help='simulated outing length')
    p.add_argument('--initial-wait', type=int, default=240)
    p.add_argument('--cloud-wait', type=int, default=300)
    a = p.parse_args()
    c = json.loads(a.config.read_text())
    a.output.mkdir(parents=True, exist_ok=True)
    log = (a.output / 'serial.log').open('w')
    events = []
    s = serial.Serial(port=None, baudrate=115200, timeout=0.1)
    s.dtr = False  # opening the port must not reset the board
    s.rts = False
    s.port = c['port']
    s.open()

    def event(name, **kw):
        events.append({'name': name, 'unix': round(time.time(), 3), **kw})
        print(json.dumps(events[-1], ensure_ascii=False), flush=True)

    def read_line():
        line = s.readline().decode(errors='replace').strip()
        if line:
            log.write(line + '\n')
            log.flush()
            if line.startswith(('STATUS', 'ERROR')):
                print(line, flush=True)
        return line

    def read_for(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            read_line()

    def query(cmd, key, timeout=25):
        """Send a one-letter command; return the first JSON reply containing key."""
        s.write(cmd)
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            line = read_line()
            if line.startswith('{'):
                try:
                    v = json.loads(line)
                except ValueError:
                    continue
                if key in v:
                    return v
        raise TimeoutError(f'no {key} reply to {cmd!r}')

    def network(timeout=25):
        s.write(b'N')
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            line = read_line()
            if line.startswith('STATUS,network'):
                return dict(x.split('=', 1) for x in line.split(',')[2:])
        raise TimeoutError('no network reply')

    result = {'events': events}
    try:
        read_for(3)
        if a.provision:
            s.write(('U' + c['url'] + '|' + c['bypass'] + '|' + c['token'] + '\n').encode())
            end = time.monotonic() + 10
            ok = False
            while time.monotonic() < end and not ok:
                line = read_line()
                if 'cloud_config_invalid' in line:
                    raise SystemExit('board rejected the configuration')
                ok = 'cloud_configured' in line
            assert ok, 'configuration not acknowledged'
            event('provisioned')

        event('wait_home_idle')
        end = time.monotonic() + a.initial_wait
        cloud = query(b'Q', 'configured')
        while cloud['mode'] != 'home' and time.monotonic() < end:
            read_for(5)
            cloud = query(b'Q', 'configured')
        event('home_state', cloud=cloud)
        assert cloud['configured'], cloud
        net = network()
        assert net.get('connected') == '1', net
        ip = net['ip']

        event('leave_home_wifi')
        s.write(b'O')
        read_for(a.seconds)
        rec = query(b'L', 'recording')
        assert rec['recording'], rec
        event('recording_while_away', recording=rec)
        sid = rec['id']

        event('return_home_wifi')
        s.write(b'W')
        end = time.monotonic() + 90
        stopped = None
        while time.monotonic() < end:
            read_for(3)
            v = query(b'L', 'recording')
            if not v['recording']:
                stopped = v
                break
        assert stopped, 'automatic stop at home did not happen within 90 s'
        event('auto_stopped_at_home', recording=stopped)

        local = requests.Session()
        local.trust_env = False
        base = 'http://' + ip
        sessions = local.get(base + '/api/sessions', timeout=40)
        sessions.raise_for_status()
        (a.output / 'board_sessions.json').write_text(sessions.text)
        raw = local.get(base + '/api/session', params={'id': sid, 'format': 'bin'}, timeout=60)
        raw.raise_for_status()
        data = raw.content
        (a.output / f'{sid}.bin').write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        event('local_session_saved', id=sid, bytes=len(data), sha=sha, samples=(len(data) - 32) // 24)

        headers = {'OAI-Sites-Authorization': 'Bearer ' + c['bypass'],
                   'Authorization': 'Bearer ' + c['token']}
        end = time.monotonic() + a.cloud_wait
        receipt = None
        while time.monotonic() < end:
            read_for(10)
            r = requests.get(c['url'] + '/api/device/status',
                             params={'id': sid, 'size': len(data), 'sha': sha},
                             headers=headers, timeout=30)
            if r.status_code == 200 and r.json().get('complete') and r.json().get('sha') == sha:
                receipt = r.json()
                break
            event('cloud_poll', http=r.status_code, body=r.text[:120])
        assert receipt, 'website did not confirm the session in time'
        event('cloud_receipt_verified', receipt=receipt)
        read_for(5)
        result.update(id=sid, sha=sha, bytes=len(data), receipt=receipt,
                      device_cloud=query(b'Q', 'configured'), passed=True)
    except BaseException as error:
        result.update(passed=False, error=repr(error))
        raise
    finally:
        s.write(b'W')  # never leave the radio off
        (a.output / 'result.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))
        log.close()
        s.close()


if __name__ == '__main__':
    main()
