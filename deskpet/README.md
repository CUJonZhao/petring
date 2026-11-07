# DeskPet

macOS-first desktop pet prototype. It runs independently of PetRing hardware.

## What works

- A transparent, movable 3D pet window that stays above normal windows.
- A locally authored, stylized 3D Delta model with blue-merle markings, a white chest ruff, a narrow muzzle, different eye colors, and an articulated head, jaw, tail, and two-part legs. Rest turns once, folds the legs, lies down, and closes its eyes. Drink walks to a water bowl, lowers the head, laps with a visible tongue, and makes water ripples.
- Local import of reference photos, grouped by angle. Photos are copied to `~/Library/Application Support/DeskPet/` and are not committed to the repository.
- Import a USDZ scene to replace the built-in model. Rigged behavior animations for arbitrary imported scenes are not yet supported; whole-model state changes still work.
- Manual event simulation, a local mock gateway and a WebSocket event client for a future gateway.
- If live events stop for 15 seconds, the pet shows `unknown` instead of pretending to be live.

The built-in model is hand-authored from the supplied photos, including a distant standing side view. It is deliberately stylized and is not a photogrammetric reconstruction. A realistic 3D asset will need closer, level full-body views, careful sculpting and a production rig; the app does not claim to generate such a model from photos yet.

Project direction: [DeskPet Proposal](PROPOSAL.md). Latest handoff: [2026-11-07 work report](docs/2026-11-07_daily_report.md).

## Build

Requires macOS 14 or later and Apple Command Line Tools with Swift 5.10 or later.

```sh
cd deskpet
xcrun swift build
./scripts/build_app.sh
open .build/DeskPet.app
```

The editable model source is `Resources/Delta.blend`. To rebuild `Resources/Delta.usdz`, run `scripts/build_delta_model.py` in Blender 5.2 or later. `scripts/render_delta_preview.py` renders a local QA preview. Neither script uploads reference photos.

To run a local event stream without hardware:

```sh
python3 scripts/mock_gateway.py
```

Then enter `ws://127.0.0.1:8765/events` in the app and click Connect.

## Event contract

The app accepts WebSocket text or binary JSON messages such as:

```json
{"state":"walk","confidence":0.9,"timestamp":"2026-11-07T16:00:00Z"}
```

`state` is `idle`, `rest`, `walk`, `drink`, `bark`, or `unknown`.
Messages with confidence below `0.6` are ignored. The gateway should send a state heartbeat at least every 10 seconds. The app uses its receive time for freshness, so a clock mismatch cannot make a stale status appear fresh. This is a development interface; pairing, authentication, reconnect and cloud relay remain for the hardware integration phase.
