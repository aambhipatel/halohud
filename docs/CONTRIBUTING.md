# Contributing to HaloHUD for Assetto Corsa

## Prepare a change

Use the setup commands in the [README](../README.md). Keep changes focused and explain the user-visible problem and resulting behavior. Submit a patch to the person maintaining your copy, or a pull request if the hosting repository supports them; no public remote or named maintainer is configured here.

## Implementation conventions

- Keep CSP access in the app adapter; keep telemetry and animation logic testable with plain Lua tables.
- Verify new APIs against the generated CSP SDK and record the baseline in [API-VERIFICATION.md](API-VERIFICATION.md). Do not guess field names or custom-car state encodings.
- Preserve existing config keys and unknown INI sections. Put defaults and clamps in settings.lua.
- Edit source generators for asset changes, then regenerate textures and glyph metadata. Use original artwork and retain font license notices.
- Record the source of car-profile values. Keep camera examples separate; do not unpack packed car data or modify the car as part of the app.

## Validate and submit

Run the offline suite from the project root:

```powershell
python -m unittest discover -s tests -v
```

Use [TESTING.md](TESTING.md) for relevant in-game checks. For rendering changes, regenerate and inspect previews; for new SDK calls, run tests/verify_sdk.py against the stated baseline. State clearly which checks were run and which remain pending. Offline mocks do not prove performance or native input behavior.

Update documentation for behavior/config changes. Rebuild packages after checks pass so generated listings and hashes match the release. Include before/after images for visual changes and car/session details for telemetry fixes. Do not include proprietary car assets, personal machine paths, private logs or downloaded SDK archives in a contribution.
