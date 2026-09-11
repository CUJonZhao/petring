#!/usr/bin/env python3
"""Physical USB bench: record, disable ESP32 Wi-Fi, export, reset, re-export.

Requires requests and pyserial. Deliberately creates short test sessions and
resets the attached board; never deletes sessions or changes saved Wi-Fi details.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import queue
import statistics
import threading
import time

import requests
import serial

from decode_motion_log import convert


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=120)
    args = parser.parse_args()
    if args.seconds < 60:
        parser.error('Use at least 60 seconds')
    args.output.mkdir(parents=True, exist_ok=True)
    http = requests.Session()
    http.trust_env = False
    device = serial.Serial(port=None, baudrate=115200, timeout=.15)
    device.dtr = False
    device.rts = False
    device.port = args.port
    device.open()
    done = threading.Event()
    status_lines = queue.Queue()
    errors = []
    events = []

    def event(name, **fields):
        value = {'event': name, 'host_unix': time.time(), **fields}
        events.append(value)
        print(json.dumps(value), flush=True)

    def capture():
        with (args.output / 'serial.log').open('wb') as log:
            while not done.is_set():
                line = device.readline()
                if not line:
                    continue
                log.write(line)
                text = line.decode(errors='replace').strip()
                if text.startswith('ERROR'):
                    errors.append(text)
                if text.startswith('{'):
                    try:
                        status_lines.put(json.loads(text))
                    except ValueError:
                        pass

    reader = threading.Thread(target=capture, daemon=True)
    reader.start()

    def get(path, method='GET', **kwargs):
        response = http.request(method, args.url.rstrip('/')+path, timeout=15, **kwargs)
        response.raise_for_status()
        return response

    def wait_online(seconds=30):
        deadline = time.monotonic()+seconds
        while time.monotonic() < deadline:
            try:
                return get('/api/recording').json()
            except requests.RequestException:
                time.sleep(.5)
        raise RuntimeError('Device did not reconnect')

    def status_serial():
        while not status_lines.empty():
            status_lines.get_nowait()
        device.write(b'L')
        result = status_lines.get(timeout=5)
        assert result['ready'] and result['recording'], result
        return result

    def pause_until(start, seconds):
        delay = start+seconds-time.monotonic()
        if delay > 0:
            time.sleep(delay)

    try:
        initial = wait_online()
        assert initial['ready'], initial
        get('/api/recording/stop', 'POST')
        started = get('/api/recording/start', 'POST', data={'unix_ms':str(int(time.time()*1000))}).json()
        assert started['recording'], started
        sid = started['id']
        start = time.monotonic()
        event('recording_started', id=sid)
        denied = http.get(args.url+'/api/session?id='+sid, timeout=5)
        assert denied.status_code == 409
        pause_until(start, args.seconds/4)
        before_offline = get('/api/recording').json()
        device.write(b'O')
        event('wifi_disabled', saved_samples=before_offline['saved_samples'])
        pause_until(start, args.seconds/2)
        offline = status_serial()
        assert offline['id'] == sid and offline['saved_samples'] > before_offline['saved_samples']
        try:
            http.get(args.url+'/api/recording', timeout=2)
        except requests.RequestException:
            network_unreachable = True
        else:
            network_unreachable = False
        assert network_unreachable, 'Wi-Fi request unexpectedly succeeded while radio disabled'
        event('offline_recording_confirmed', saved_samples=offline['saved_samples'])
        pause_until(start, args.seconds*3/4)
        device.write(b'W')
        online = wait_online()
        assert online['id'] == sid and online['recording']
        event('wifi_reconnected', saved_samples=online['saved_samples'])
        pause_until(start, args.seconds)
        stopped = get('/api/recording/stop', 'POST').json()
        assert not stopped['recording'] and not stopped['error'], stopped
        csv_response = get('/api/session?id='+sid+'&format=csv')
        binary = get('/api/session?id='+sid+'&format=bin').content
        (args.output / (sid+'.bin')).write_bytes(binary)
        (args.output / (sid+'.csv')).write_bytes(csv_response.content)
        rows = list(csv.DictReader(io.StringIO(csv_response.text)))
        assert len(rows) == int(csv_response.headers['X-Delta-Records']) == stopped['saved_samples']
        decoded = convert(args.output/(sid+'.bin'), args.output/(sid+'-decoded.csv'))
        assert decoded['records'] == len(rows) and not decoded['warnings']
        decoded_rows = list(csv.DictReader((args.output/(sid+'-decoded.csv')).open()))
        assert len(decoded_rows) == len(rows)
        for remote, local in zip(rows, decoded_rows):
            assert remote['elapsed_ms'] == local['elapsed_ms'] and remote['state'] == local['state']
            for key in ('ax_g','ay_g','az_g','gx_dps','gy_dps','gz_dps','temp_c','motion_g','activity_score','battery_v'):
                assert abs(float(remote[key])-float(local[key])) < .0002, (key,remote[key],local[key])
        elapsed = [int(row['elapsed_ms']) for row in rows]
        intervals = [b-a for a,b in zip(elapsed,elapsed[1:])]
        assert all(dt>0 for dt in intervals)
        event('download_verified', records=len(rows), bytes=len(binary))

        # End a second recording by a hardware EN reset. USB power remains on.
        interrupted = get('/api/recording/start', 'POST').json()['id']
        time.sleep(4.35)
        before_reset = get('/api/recording').json()
        assert before_reset['saved_samples'] >= 40
        device.rts = True
        time.sleep(.15)
        device.rts = False
        time.sleep(2)
        after_reset = wait_online()
        assert after_reset['recording'] and after_reset['id'] not in (sid,interrupted)
        get('/api/recording/stop','POST')
        sessions = get('/api/sessions').json()
        by_id = {s['id']:s for s in sessions['sessions']}
        assert by_id[sid]['state'] == 'complete'
        assert by_id[interrupted]['state'] == 'interrupted'
        repeated = get('/api/session?id='+sid+'&format=bin').content
        assert repeated == binary
        recovered = get('/api/session?id='+interrupted+'&format=bin').content
        (args.output/(interrupted+'-interrupted.bin')).write_bytes(recovered)
        recovery = convert(args.output/(interrupted+'-interrupted.bin'), args.output/(interrupted+'-interrupted.csv'))
        assert recovery['records'] >= before_reset['saved_samples']
        battery = get('/api/battery-log').content
        (args.output/'battery_after.csv').write_bytes(battery)
        result = {'session_id':sid,'duration_ms':elapsed[-1], 'records':len(rows),
                  'effective_hz':(len(rows)-1)*1000/(elapsed[-1]-elapsed[0]),
                  'interval_ms':{'min':min(intervals),'median':statistics.median(intervals),'max':max(intervals),'over_100':sum(x>100 for x in intervals)},
                  'temperature_c':{'min':min(float(r['temp_c']) for r in rows),'max':max(float(r['temp_c']) for r in rows)},
                  'binary_bytes':len(binary),'sha256':hashlib.sha256(binary).hexdigest(),
                  'csv_binary_agree':True,'wifi_off_recording':True,'reset_identical_completed_file':True,
                  'interrupted_session':interrupted,'interrupted_recovered_records':recovery['records'],
                  'storage_after':get('/api/recording').json(),'sessions_after':sessions,
                  'serial_errors':errors,'events':events,
                  'limitations':['USB-powered, not a battery-runtime test','EN reset, not a physical power cut','Full-disk behavior not exercised on device']}
        (args.output/'result.json').write_text(json.dumps(result,indent=2))
        event('PASS', **{k:v for k,v in result.items() if k not in ('events','sessions_after','storage_after')})
    finally:
        # Restore Wi-Fi even when an assertion fails; stop test recording so the
        # board does not silently consume the remaining flash after the test.
        try:
            device.write(b'WS')
            time.sleep(.3)
        except serial.SerialException:
            pass
        done.set()
        reader.join(timeout=2)
        device.close()
        (args.output/'events.json').write_text(json.dumps(events,indent=2))


if __name__ == '__main__':
    main()
