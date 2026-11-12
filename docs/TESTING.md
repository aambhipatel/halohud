# Verification and acceptance checklist

## Tests performed in this environment

- [x] All six Lua files parse using a Lua 5.1 runtime (Lupa's Lua 5.1 module).
- [x] Direct mapping preserves 296.25 km/h, 13,250 RPM and seventh gear with no temporal smoothing.
- [x] The 70 ms exponential pedal step reaches `1-exp(-1)` at 70 ms.
- [x] Non-KERS cars do not display invented charge/overtake values.
- [x] Full throttle does not imply the overtake button is pressed.
- [x] Missing physics disables unavailable ERS, pedal and DRS inputs.
- [x] NaN/infinity and out-of-range normalized inputs are handled safely.
- [x] P1, solo, empty and sparse leaderboard cases do not dereference a missing opponent.
- [x] Surnames, three-letter codes, common accented names and overly long names are handled.
- [x] Synthetic values cover R, N, 1–8, both pedals and charge within bounds.
- [x] AUTO no-car demo, OFF no-car hiding and live solo/no-KERS app execution work in the CSP interface mock.
- [x] Quad geometry, opacity, assets and UV bounds pass at 1280×720, 1920×1080, 2560×1440 and 3440×1440; curve 0/1/1.6 and all three themes are exercised.
- [x] Static artwork and preview files are generated from the supplied source; there are no missing texture placeholders.
- [x] The actual Lua draw stream was rendered for visual inspection, with a second confirmation after correcting RPM caption spacing.
- [x] Runtime API calls and accessed telemetry fields match declarations in the official CSP 0.2.0 generated SDK.

Run `python -m unittest discover -s tests -v` to repeat the 52 automated tests. The interface mock does not prove engine integration, FFI behavior, texture loading or performance. The no-car test models a fallback state; ordinary AC sessions normally contain a player car.

## Required in-game checks — not performed here

Install in an offline session first. Record AC version, CSP build, car/mod version, track, screen resolution, UI scale, CPU/GPU, frame cap and graphics preset. Keep Force demo telemetry **off** for live comparisons.

| Case | Expected result | Pass |
|---|---|---|
| App discovery | HaloHUD controls appears and opens; no Lua error in log. | [ ] |
| Transparent HUD | No opaque rectangular window; clicks pass through; closing controls leaves the HUD visible. | [ ] |
| 1080p reference comparison | Center dial ~20% of HUD width; five regions recognizable; teal rim, navy glass, blue tabs and green throttle match the intended composition. | [ ] |
| Actual halo camera | Camera clears the mesh, sees nose/front wheels, 70–75° starting FOV; scale/Y/curve align with the car. | [ ] |
| Live speed | At standstill, 100 km/h and high speed, primary/secondary rounded speeds agree with Python `ac.getCarState(0, acsys.CS.SpeedKMH)` and the game. | [ ] |
| MPH-first | `UNITS=MPH` swaps the values and their unit labels correctly. | [ ] |
| RPM | `rpm` equals Python `acsys.CS.RPM`; bar occupies `clamp(rpm/RPM_MAX)` of configured range. | [ ] |
| Gears | CSP 0=N, -1=R and forward numbers agree with the car. Python Shared Memory/CS gear encodings may be offset; normalize before comparison. | [ ] |
| Pedals | Controls' raw values agree with Python `acsys.CS.Brake` / `Gas`; graphic damping is 70 ms time constant. Both columns fill bottom-up. | [ ] |
| Standard KERS car | Charge matches CSP `kersCharge`; deploy indicator follows `kersInput`; recharge follows `kersCharging`. | [ ] |
| Overtake button | Highlight follows `kersButtonPressed`, independent of normal automatic deployment. | [ ] |
| No KERS | NO ERS/-- shown, empty charge; no Lua error. | [ ] |
| DRS | Dashes change only with present/available/active DRS states. | [ ] |
| P1 and solo practice | P1 with opponents retains CLEAR TRACK; solo has one centered player row and highlight, no CLEAR TRACK; no crash. | [ ] |
| Qualifying/practice | Opponent row follows session lap-time leaderboard, not track distance. | [ ] |
| Opponent disconnect / session reset | Missing entries clear safely and player row refreshes within 250 ms. | [ ] |
| Replay | Player-car telemetry remains selected; unavailable physics gets PHYSICS N/A and no stale ERS. | [ ] |
| Resolution/UI scale | No stretching/clipping at target resolution; offsets/scale respond after reload and after resizing. | [ ] |
| Demo transition | Demo label always visible in synthetic mode; turning it off returns to the real car. | [ ] |
| Long session | Run 30 minutes; text cache stays bounded and performance remains stable. | [ ] |

For Python comparison use the SDK shipped with your AC installation (`sdk/dev`); this package does not install or rely on a Python app. A Python value with a different documented gear/ERS encoding is not a direct numeric comparator. The controls window exposes unrounded canonical speed/RPM/gear/pedal/ERS values for comparison against CSP's Lua Debug console. Charge and normalized KERS input are distinct from per-lap energy budgets or electrical power.

If a hybrid mod uses private shared-memory channels, that requires its own verified adapter. Passing on a standard KERS car does not establish compatibility with every such mod.

## 0.3 ms performance gate — pending

1. Use a repeatable replay/scene, fixed graphics settings, stable temperatures and an uncapped or consistently capped render loop. Disable unrelated telemetry apps for the isolation pass.
2. Warm up at least 30 seconds after first opening/reloading the HUD. Texture uploads, static mesh construction and initial text caches are not steady-state costs; record first-use hitches separately.
3. Enable **Measure Lua CPU time** temporarily. Check update + draw submission. Reset peak by toggling profiling off/on after warm-up. Capture the displayed values or use your build's Lua profiler for a distribution; the in-app readout gives current and peak timings, not p95.
4. Record a 60-second baseline with **Show HUD** off, then 60 seconds on, then repeat the pair three times. Close the controls window for the external frame-time pass. Record CPU and GPU frame times using the CSP profiling tools available in your build or a reliable external frame-time capture tool.
5. Compare medians and p95 across paired runs. Acceptance requires attributable total frame-time increase **≤0.3 ms** on the target system, with measurement noise reported. The Lua CPU span alone cannot establish the GPU or total frame-time claim. An FPS delta under vsync is not adequate evidence.
6. If it fails, set `CURVE_STRIPS=8`, reload, warm up and repeat. If that still fails, profile draw submission/texture switches and atlas batching before claiming compliance. Keep the visual comparison at the chosen quality setting.

This environment has no Assetto Corsa installation, so no measured sub-0.3 ms or live telemetry acceptance claim is made.


## Version 1.1 historical checks (superseded by 1.2 below)

Offline: 20 tests pass, including equal digit-cell centers/advances; all 16 combinations of 0.5/1.5 region scales at curve 0 and 1.6 with maximum overall scale and edge offsets; live slider application; complete Save/Reset through an INI mock; preservation of MPH/theme; disabled-state loading; positive/negative/quantized recovery, timeout, charging gating, full battery, invalid samples, long-frame resets, and default-empty versus opt-in DRS fallback.

The user confirmed v1.0 runs in AC and looks good. Version 1.1 still requires the following in-game confirmation:

- [ ] Move every slider while parked: placement changes without reload; independently shrink side panels while keeping dial scale fixed. At fit limits the whole composition caps its effective size.
- [ ] Save, restart AC, verify every known option persists; check unrelated INI sections remain. Reset previews defaults and Save persists them.
- [ ] Check tab fills at 0/0.5/1, upward order, dim inactive segments, readable overlaid labels and rounded silhouette. Confirm approximately 70 ms damping.
- [ ] Compare charge derivative with raw CSP values; try RECOVERY_FALLBACK=EMPTY on quantized/unmeasurable cars. Verify no recovery when charging=false or battery full.
- [ ] Non-KERS default: both tabs empty with NO ERS. Optional DRS mode: DEPLOY follows active DRS and RECHARGE remains empty.
- [ ] Verify 108/184/111/888 in both unit orders: stable cell spacing, no one-sided “1” gap.
- [ ] DEMO appears small and translucent above the dial, clear of the steering-wheel display in the target camera.
- [ ] Toggle OUTER_ARC and test with all region scales; check clearances and thin teal stroke.
- [ ] Repeat the warmed-up performance gate with arc on/off. Slider-driven cache rebuilds are interactive work and should be measured separately.

SDK declarations alone do not document p2pStatus encodings. The opt-in DRS_OR_P2P fallback requires an explicitly configured P2P_ACTIVE_STATUS; default −1 disables it. Offline tests use an arbitrary fixture value to verify matching, without claiming a real-car state encoding. Verify the actual active status on your car before enabling.


## Version 1.2 current checks

25 offline tests pass. The user confirmed earlier in-game operation; no live AC session was controlled for 1.2. All 18 assets were regenerated and dimensions verified.

- [x] Player-highlight quads match panel-rim quads exactly (vertices, UVs, strip count) at curve 0/1/1.6. Both use the same shared end skew.
- [x] Actual draw-stream render shows even lower/end gaps and centered player text. Highlight-inset-verification.png includes measurement lines. Seventeen samples at each tested curvature give less than 0.01 UI pixel variation along the bottom inset; its default projected gap is about 12.018 UI pixels. The 12-pixel normal inset is defined in the design ribbon; arbitrary perspective/scaling does not imply identical raster distance on every edge.
- [x] Continuous energy-mask interior has no segmentation/dividing lines. A half-filled tab uses cropped UV 0.5..1 and half height, with rounded-mask geometry retained. Zero remains dim/empty.
- [x] Runtime renderer has no sponsor-tag string/draw commands. Current previews/demo regenerated.
- [x] Default non-KERS DRS fallback works with NO ERS, empty recharge and no guessed P2P code. Explicit legacy EMPTY remains available.
- [x] Exact car-ID profile uses live limiter/gear count when available, explicit overrides first, generic fallback otherwise. Other car IDs are isolated. Profile save preserves unknown keys and unknown capacity -1.
- [x] API declaration check includes ac.getCarID, car.gearCount and car.rpmLimiter.
- [x] Read-only car inspection: UI, extensions, display scripts, template and KN5 hierarchy. data.acd was not opened/unpacked/modified. No original car files changed.

Required in-game follow-up:

- [ ] Inspect the curved highlight at default and extreme scales, including both slanted ends and centered text.
- [ ] Check 0%, partial and 100% continuous fills, rounded corners, white labels and default 70 ms smoothing. Confirm charging-gated recovery and chosen fallback behavior against raw CSP values.
- [ ] Confirm the actual live formula_ultra_26 limiter and forward gear count in controls; ensure tick maximum and exact rev-limit indication match. Do not treat fictional 12,000 RPM / six-gear test fixtures as this mod's specs.
- [ ] Verify a different car uses generic HUD settings. Save/reload/reset both sections and inspect preserved config keys.
- [ ] Obtain loose files/transforms listed in CAR-PROFILE.md, then calibrate recovery/capacity and camera. Until then the car-specific camera example is a non-executable merge guide.
- [ ] Verify wheel-screen/HUD/DEMO clearance with that calibrated camera; current model bounds alone cannot prove screen-space clearance.
- [ ] Repeat the warmed-up on/off CPU/GPU comparison for the 0.3 ms target. Texture uploads, interactive resizing and cache construction are separate from steady-state cost.


## Version 1.3 current checks

- [x] 29 offline tests pass, including actual renderer text capture for 0/1/9/17/99/108/184/296 in KMH-first and MPH-first modes with no leading zero padding.
- [x] Both pedal columns contain 16 segments ordered bottom-up in the existing module envelope; damping remains unchanged.
- [x] Inactive aero renders / / for present and absent DRS; active aero retains its original two-dash geometry.
- [x] Solo selects a centered highlight mask and shifts player text by the same 42 design pixels. No CLEAR TRACK text is drawn. The real simulation car count prevents an incomplete multiplayer leaderboard from falsely activating solo mode.
- [x] Solo and ordinary layouts transition correctly, preserving frame skew/curvature. Assets and offline previews regenerated.
- [ ] In AC, check 0, 9, 17, 99 and 100 speed transitions in both unit orders, the finer pedal fill, active/inactive aero, and solo-to-multicar sessions.

Solo is defined by simulation carsCount==1, including its pit state; this does not classify a multiplayer session as solo merely because its other cars are parked in pits. Existing car-profile/camera export limitations remain as documented in CAR-PROFILE.md.


## Version 1.3.1 race-position regression

- [x] 32 offline tests pass. Player index 0 with racePosition=3 is displayed P3 even when session.leaderboard lists the player first.
- [x] Changes from P3 to P2 to P1 and back update both player and preceding-driver rows using live per-car racePosition.
- [x] Missing/invalid rank and missing preceding car clear stale data to UNAVAILABLE, not CLEAR TRACK. True P1 and solo retain their distinct behaviors.
- [x] Actual app callback test covers bot-race classification and repeated refreshes with a deliberately incorrect player-first board.
- [x] racePosition, isConnected, isActive, raceSessionType and SessionType.Race declarations verified in the generated CSP 0.2.0 SDK.
- [ ] Start an offline race with bots, pass/be passed, and compare the controls Position/Ahead line with the native race tower. Updates should appear within 250 ms. Repeat after session restart and check practice/qualifying ordering.


## Version 1.4 current acceptance

- [x] 37 offline tests pass. Boundary tests cover RPM 9,999/10,000/10,001/13,000 with an unrelated configured limiter, and deploy 49%/50%/51% with the overtake button both pressed and released.
- [x] OVERTAKE remains plain; BOOST alone receives the deploy-controlled green highlight. TURN removed. Current previews and embedded demo regenerated and render inspected.
- [x] Settings debounce restarts on subsequent edits. Edits save while controls are closed and even if the HUD is disabled. Save still writes immediately; demo/profiling/arc persist through reload.
- [x] Failed saves display the error and retry. Pending edits flush on the verified CSP onRelease callback.
- [ ] In AC, confirm the same threshold behavior, then edit settings, wait for Saved config.ini, restart the session and verify persisted values. Inspect the actual file path apps/lua/HaloHUD/config.ini. A read-only installation should show an error rather than a success message.

Earlier sections document historical behavior; this version's fixed RPM threshold and automatic persistence supersede the prior limiter-color and manual-save-only rules.


## Version 1.4.1 current checks

- [x] 38 offline tests pass. RPM threshold cases now include 10,000, 10,999, 11,000, 11,001 and 13,000: only values strictly above 11,000 are red.
- [x] Inactive BOOST and plain OVERTAKE have separate grey outlines/fills; active BOOST retains green. Lua aero logic remains unchanged.
- [x] Animation HTML JavaScript smoke test covers opposite rotation directions, exact active line lengths, reverse transition, duration control and scrubbing. The preview is not an engine integration test or an implemented Lua feature.
- [x] User approved revised parallel-rotation HTML; implemented in Lua v1.5.
- [ ] Confirm grey box readability and the 11,000 RPM threshold in AC.


Aero preview revision 2 supersedes the opposite-rotation study. JavaScript tests verify both clockwise angles, exact endpoints, reverse activation, position/velocity continuity at a mid-transition toggle, and nonintersecting line capsules at 1,001 scrubbed phases. Minimum stroke clearance is 8.57 design pixels. Lua animation remains unimplemented pending review.


## Version 1.5 current acceptance

- [x] 42 offline tests pass. Actual approved HTML JavaScript and Lua motion produce matching phase/velocity values (tolerance 1e-10) across mixed frame intervals, target switches and rapid reversals.
- [x] SAT polygon tests verify no overlap at 101 phases for curves 0/1/1.6 and right scales 0.5/1.5. Both bars have identical angles throughout; active endpoints match the previous short upper/long lower dashes.
- [x] Reversal preserves position/velocity; 60/120 Hz steps agree. Renderer rebuild during motion does not restart the phase.
- [x] Timing defaults to 420 ms, is range-clamped and handled by the existing settings schema/autosave.
- [x] Actual Lua inactive/intermediate/active render inspected in Aero-Lua-motion.png. Demo and previews regenerated.
- [ ] In AC, activate/deactivate DRS repeatedly, including a mid-transition toggle; check direction, clearance, colors and perceived timing. Resize during motion and verify the phase continues. Save timing, restart and verify persistence.

No fresh engine-performance or live-car acceptance claim is made; existing camera/physics export limitations still apply.


## Version 1.5.1 HUD visibility

- [x] 44 offline tests pass. appsHidden and uiHidden independently suppress all overlay draw commands and restore drawing when cleared.
- [x] Global hide/show leaves the saved ENABLED preference untouched. A separately disabled HUD stays disabled when global HUD visibility returns.
- [x] Pending settings save while globally hidden and while Show HUD is disabled.
- [x] appsHidden/uiHidden verified in generated CSP 0.2.0 SDK, StateUi lines 4142–4143.
- [ ] In AC, press Ctrl+H repeatedly: HaloHUD should hide/show with the other apps. Repeat with Show HUD disabled, then enabled. Verify live values/animation remain current when shown again.


## Version 1.5.2 reverse slot

- [x] 45 offline tests pass. Actual renderer capture verifies N -> R -> forward -> R -> N for six-, eight- and twelve-gear rows. Reverse is shown once at the neutral slot, with active size/color/highlight.
- [ ] In AC select reverse, neutral and first gear; verify the first slot changes and there is no extra reverse readout.


## Version 1.6 current checks

- [x] 48 offline tests pass. The integrated battery mask and upper-player highlight match the approved HTML preview pixel-for-pixel.
- [x] Actual renderer/telemetry tests cover P1 above P2, P2 below P1, centered solo, and missing second-place data. Transitions reset leaderFirst so stale upper highlights do not persist. Race rows never use CLEAR TRACK.
- [x] Brake color is red; normalized inputs, 16 segments and damping remain unchanged. Battery fill crops the solid silhouette at the requested charge; no-KERS retains a dim empty battery.
- [x] Integrated P1 render inspected; all 20 PNG assets regenerated, including the new upper-row highlight. Existing DRS motion, Ctrl+H, reverse slot and persistence regressions still pass.
- [ ] In AC compare the new battery/red brake appearance with the approved preview. Pass/be passed at P1/P2, check both drivers and highlights, then test solo and session restart. Check no-KERS battery fallback.

Earlier CLEAR TRACK race behavior and battery-outline descriptions are historical and superseded by this release. Practice/qualifying continue using the existing leaderboard behavior.


## Mouse positioning (1.7)

- [x] 52 offline Lua 5.1 tests pass, including mouse movement at 1280x720, 1920x1080 and 2560x1440, scale conversion, edge clamps/reversal, first-click stability, save debounce, temporary mode, Reset and global hiding.
- [x] New mouse APIs checked against generated CSP 0.2.0 build 2651 SDK declarations. Fullscreen window still rejects input; only the small edit handle accepts it.
- [ ] In AC, enable **Drag HUD with mouse**, close controls, left-drag the handle, release and wait 0.4 seconds. Reopen controls: offsets match. Reload/restart: position is retained.
- [ ] Move to all edges at different resolutions/UI scales and overall/region scales. No jump on initial click, clipping, or dead zone when reversing direction. Confirm mouse movement does not move the driving camera while holding the handle.
- [ ] Turn edit mode off: no handle/input capture. Ctrl+H hides HUD and handle; showing it does not resume a stale drag. Reset ends edit mode. Startup begins with edit mode off.

Mouse tests use an input mock, so actual CSP mouse capture, UI scaling and click routing remain in-game checks.


## Curved gauges and battery contrast (1.8.0)

- Offline: 56 tests cover equal-length pedal masks, bottom-up segment order, continuous empty/half/full energy fills, distinct battery colors/cropping, and existing scale/drag/visibility/telemetry regressions.
- In game: check the close energy/dial gap, fitted pedal borders, lower labels and DEPLOY spacing at normal and extreme dial/module scales. Verify brake/throttle, recharge/deploy and battery at 0/50/100% against live telemetry.
- Check the depleted/charged battery contrast over gray and bright liveries. Check Ctrl+H and drag positioning. Measure warmed-up CPU/GPU frame time; performance and native integration remain unverified offline.
