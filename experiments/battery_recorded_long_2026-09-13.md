# Battery-powered long recording — 2026-09-12/13

## Purpose

Verify that the assembled Delta prototype can continuously sample and save IMU
data on its LiPo for at least one hour, then return the session to the private
website without a cable-side export.

## Procedure

- The board was charged over USB, then USB was removed with the external
  battery switch left on.
- After the board rebooted on battery and rejoined home Wi-Fi, a manual
  recording (`bfe0a2f2`) was started through the local recorder endpoint at
  2026-09-12 21:57:09.
- The device was left stationary. The intended duration was one hour, but the
  operator returned later than planned and reconnected USB at about 02:59.
- The private website was inspected after reconnecting; it had already received
  and integrity-checked the immutable binary file at 00:19:44.

## Results

| Measure | Result |
|---|---:|
| Website record span | 130 min 38 s (7,838 s) |
| Valid samples | 150,289 |
| Whole-span effective rate | 19.174 Hz |
| Reported sampling gaps | 6 min 19 s (4.84% of span) |
| Activity classification | 130 min 38 s rest; walk/run 0 s |
| Activity index | 1.5 mg |
| Battery during saved record | 3.83 V to 3.59 V |
| Website file size | 3,522.4 KiB |
| Cloud file integrity | Passed by the website |

The website labels the record as not normally ended. Its duration ended around
00:07:47, well before the later USB reconnect, and the recorder had begun with
about 3.76 MiB free. The observed 3.52 MiB file size and the firmware's
reserve-based recorder behavior make **storage-full automatic stop** the most
likely explanation. This is an inference from the timing, website status, and
firmware behavior; the device-side file had already been cloud-confirmed and
pruned before inspection, so its final local status marker was no longer
available.

After USB was reconnected, the board rebooted and initially reported 3.322 V.
It rose to 3.464 V over the following roughly two minutes, confirming that the
charger was active on this connection.

## Conclusion

**PASS for the one-hour recorded battery requirement.** The session exceeded
the target by 70 min 38 s, persisted 150k samples, survived low-voltage runtime,
and reached the private website with an integrity-checked binary. It does not
demonstrate a controlled one-hour manual stop, and the current recorder's
practical capacity is about 130 minutes at the observed sampling rate.

The next product validation is a short supervised real walk: begin on battery,
leave the home network, return home, and confirm automatic close/upload and the
website summary. Keep the recording below roughly one hour so the session ends
under normal control rather than at its storage limit.
