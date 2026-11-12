# CSP API verification

Version 1.2 rechecked `ac.getCarID` (2445), `car.gearCount` (3696, excluding N/R) and `car.rpmLimiter` (3753) in the same generated 0.2.0 baseline. They supply live powertrain adaptation only for the matching car profile. No packed INI reader is used. Continuous tabs use the existing verified drawImageQuad API with cropped UVs; timing text, frame and highlight share one transform. No new unverified camera or custom-aero API is introduced.

The authoritative baseline used here was extracted from the official **CSP 0.2.0 ZIP**, version code **2651**, downloaded from `https://acstuff.ru/patch/?get=0.2.0`. It was not installed. Baseline declaration file:

`extension/internal/lua-sdk/ac_apps/lib.lua`

Baseline file SHA-256: `b539e88484617e4f169c8c413e9c7518ba9d96e56b556eb3432f0890fdbc883d`.

The public SDK repository contains generator directives in place of some APIs; checking only current GitHub source is insufficient to prove an older minimum version. Runtime code was checked against the generated 0.2.0 file, and every API below is present there.

| API / data | Baseline location | Use |
|---|---:|---|
| `ac.getSim()` | 3477 | Session index and car count. |
| `ac.getSession(index)` | 3483 | Session leaderboard. |
| `ac.getUI()` | 3490 | UI-scaled viewport size. |
| `ac.getCar(index)` | 3503 | Player telemetry. |
| `ac.StateCar` | 3744–3890 | Gas/brake, gear, RPM, speed, KERS and DRS fields. |
| `ac.StateLeaderboardEntry.car` | 3923–3930 | Safe ranked car lookup. |
| `ac.StateSession.leaderboard` | 3943 | 0-based entries and array length. |
| `ac.StateUi.windowSize` | 4122 | Resolution independence under CSP UI scale. |
| `ac.INIConfig:get` | 5356 | Typed config reads. |
| `ac.INIConfig.load` | 5452 | Config reload. |
| `ui.beginTransparentWindow` | 9556 | Input-free fullscreen UI. |
| `ui.endTransparentWindow` | 9560 | Matched window close. |
| `ui.text` / `ui.textWrapped` | 9568 / 9583 | Controls and status. |
| `ui.drawImageQuad` | 9810 | All HUD art, glyphs and solid-color rectangles. |
| `ui.button` | 10624 | Reload button. |
| `ui.checkbox` | 10689 | Controls. |
| `os.preciseClock` | 3430 | Optional CPU submission timing. |
| `ac.accessCarCamera` / camera parameters | 15552–15577 | Documentation check for F6 car camera model; not called by HUD. |

`driverName()` is a documented car-state method implemented in `common/ac_state.lua`; the generated baseline also declares it. Global `__dirname` is used by official CSP apps to locate their own files. Lua `require`, math/string/table functions and `pcall` are standard runtime features.

Verified quad argument order: image, top-left, top-right, bottom-right, bottom-left, tint, then the four corresponding UV coordinates. Tint is `rgbm(r,g,b,alpha)` in the UI, with the `mult` field supplying alpha. No guessed `pushRotation`, canvas-to-display binding, active-aero API or private hybrid API is used.

For compatibility with 0.2.0, the implementation uses `session.leaderboard[rank].car`, **not** the newer `ac.getCar.leaderboard()` helper. It does not rely on undocumented IN_GAME drawing context: it opens its own transparent window as the official Lua app guide requires.

## Repeat the declaration check

```powershell
python tests/verify_sdk.py "C:/path/to/assettocorsa/extension/internal/lua-sdk/ac_apps/lib.lua"
```

This reads the SDK and verifies all runtime ac/ui/os calls, accessed car fields and state/INI methods. It cannot validate C++ implementation behavior, texture output or runtime performance. A mock passing is not a substitute for the in-game checks.

## Primary references

- [Official Lua app manifest and fullscreen callback guide](https://github.com/ac-custom-shaders-patch/acc-lua-sdk/wiki/Lua-apps).
- [Official SDK README and explanation of installed generated definitions](https://github.com/ac-custom-shaders-patch/acc-lua-sdk/blob/main/README.md).
- [Official CSP 0.2.0 release information, code 2651](https://acstuff.ru/patch/?info=0.2.0).
- [Official state provider source](https://github.com/ac-custom-shaders-patch/acc-lua-sdk/blob/7cf60f5a406820ee4e39f3a62ed121fa36274001/common/ac_state.lua).
- [Official F6 camera parameter wrapper](https://github.com/ac-custom-shaders-patch/acc-lua-sdk/blob/7cf60f5a406820ee4e39f3a62ed121fa36274001/lib_carcameradef.lua).
- [Official app examples](https://github.com/ac-custom-shaders-patch/app-csp-defaults/tree/7b9a279919ecc44cf0903dbb30547c53d03a2561).

The camera INI coordinates are explicitly illustrative and untested per car. `cameras.ini` is not a portable calibration, and no claim is made that its example position fits a particular F1 mod.


Version 1.1 additionally verifies `ui.slider` (13187), `INIConfig:set` (5407) and `INIConfig:save` (5425). The energy-gauge fields remain the baseline kersInput/kersCharge/kersCharging and drsPresent/drsActive. The declared integer p2pStatus has no state-value documentation in this SDK; the opt-in fallback only matches a user-supplied verified active value. The default −1 disables it. No undocumented direct recovery-rate API is introduced.

Version 1.3.1 uses documented StateCar.racePosition (3856), isActive/isConnected (3788–3789), StateSim.raceSessionType (4066) and SessionType.Race (851–860). Race positions no longer depend on session leaderboard indices.

Version 1.4 uses verified ac.onRelease(callback) (baseline line 4352) to flush pending settings. Existing INIConfig set/save methods are unchanged.

Version 1.5.1 reads ac.getUI().appsHidden (4142, explicitly documents Ctrl+H) and uiHidden (4143). No key polling or additional hotkey binding is introduced.


## Mouse positioning (1.7)

The generated 0.2.0 baseline declares ui.setCursor (9659), ui.drawRectFilled (9877), ui.mouseDelta (10344), ui.invisibleButton (10652), ui.itemActive (10841), and ui.captureMouse (11122). The small handle uses beginTransparentWindow(..., true, true); the fullscreen overlay retains inputs=false. itemActive tracks the held invisible button; captureMouse is called only while it is active. Mouse deltas are converted through the actual renderer scale. This verifies API names/signatures, not native mouse routing or game integration.
