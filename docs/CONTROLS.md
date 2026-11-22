# HaloHUD controls

The controls window opens at 560 × 680 CSP UI units with a 390 × 340 minimum. Scale and opacity use percentages, animation and DRS timing use seconds, and the DRS margin uses metres.

- **General** has HUD visibility, Save and Reload, Lock HUD position and Debug Mode.
- **HUD** groups Layout, Panel scales, Elements, Units and colors, and Animations. Elements has three independent zone toggles: leaderboard, speedometer with its pedal and energy gauges, and active aero with gears and RPM. All three default on. The outer arc has its own toggle.
- **DRS Chime** shows enable, volume, Test chime, the sound file, trigger mode and Reset section. A warning appears when the selected WAV is missing or playback is unavailable. Debug Mode also reveals live status and editable car overrides. Force-off wins conflicts, and overrides remain active with Debug Mode off.
- **Advanced** has a collapsed DRS tuning section. Debug Mode adds Diagnostics and Live telemetry, also collapsed by default.

**Debug Mode** (`DEBUG_MODE`) and **Lock HUD position** (`LOCK_HUD_POSITION`) both default off. Debug Mode gates DRS logging, its activation-edge test, forced demo telemetry and CPU profiling while preserving their saved preferences. Automatic demo when no car is available still follows the existing DEMO fallback. Section resets require confirmation. Only **Clear both car override lists?** clears the override lists. Section resets preserve Debug Mode and Lock HUD position.

## Mouse controls

Move the mouse to the in-game app sidebar at the right edge to reveal the cursor if it is hidden. Move back over the HUD until the move cursor appears. Press and hold the left button anywhere across the HUD body and move the mouse. Release to save the position after the normal 0.4-second delay. Double-click the HUD to restore both offset sliders to 0 px. Lock HUD position disables both gestures.

The old drag pill was controlled by a session-only toggle. If a saved config explicitly has `DRAG_HUD_WITH_MOUSE` or `DRAG_MODE` set to false, the app starts locked and saves `LOCK_HUD_POSITION = 1` once. An explicit true maps to unlocked. An existing `LOCK_HUD_POSITION` takes precedence and a missing legacy key uses the new default. Existing X/Y offsets load as before.

## Previous controls inventory

All persisted rows use `[HUD]` in `apps/lua/HaloHUD/config.ini`. Defaults come from `settings.lua`. Drag edit mode is session-only. Dragging saves X and Y offsets using the existing keys.

| Previous control | Key | Type | Default |
|---|---|---|---|
| Show HUD | `ENABLED` | Boolean | On |
| Force demo telemetry | `DEMO` | Enum through a toggle | `AUTO` |
| Measure Lua CPU time | `PROFILE_CPU` | Boolean | Off |
| Drag HUD with mouse | `dragMode` | Session-only Boolean | Off |
| HUD scale | `SCALE` | Number | `1.0` |
| X offset | `X_OFFSET` | Number | `0` design px |
| Y offset | `Y_OFFSET` | Number | `0` design px |
| Curvature | `CURVE` | Number | `1.0` |
| Leaderboard animation | `LEADERBOARD_ANIMATION_MS` | Number | `450` ms |
| Gear animation | `GEAR_ANIMATION_MS` | Number | `260` ms |
| Aero animation | `AERO_ANIMATION_MS` | Number | `420` ms |
| Left timing scale | `LEFT_SCALE` | Number | `1.0` |
| Center dial scale | `DIAL_SCALE` | Number | `1.0` |
| Pedal / energy modules scale | `MODULE_SCALE` | Number | `1.0` |
| Right powertrain scale | `RIGHT_SCALE` | Number | `1.0` |
| Outer arc | `OUTER_ARC` | Boolean | Off |
| DRS chime | `DRS_CHIME_ENABLED` | Boolean | Off |
| Trigger mode | `DRS_TRIGGER_MODE` | Enum | `AUTO` |
| DRS chime volume | `DRS_CHIME_VOLUME` | Number | `0.65` |
| DRS WAV file | `DRS_SOUND` | Filename | `drs_chime.wav` |
| DRS debug logging | `DEBUG_DRS` | Boolean | Off |
| Chime on drsActive rising edge | `DEBUG_DRS_ACTIVE_CHIME` | Boolean, visible with debug logging | Off |

Test chime, Save, Reload and Reset were actions. The car profile and telemetry detail were read-only.

## Local SDK verification

The shipped CSP 0.2.0 baseline and installed SDK declare `ui.tabBar`, `ui.tabItem`, `ui.treeNode`, `ui.itemHovered`, `ui.setTooltip`, `ui.combo`, `ui.selectable`, `ui.slider`, `ui.inputText`, `ui.textColored`, `ui.styleColor`, `ui.pushStyleColor`, `ui.separator`, `ui.sameLine`, `ui.setNextItemWidth`, `ui.dummy`, `ui.availableSpaceX` and `ui.childWindow`. Both also declare window flags, font and scaling helpers and `ac.getUI().uiScale`. `ui.collapsingHeader` and `ui.colorEdit` are absent. The controls use `treeNode` for collapsed sections and keep the existing HUD themes as the color choices. The SDK offers `colorPicker` for editable colors, which the current schema does not store. Status text uses green, amber or red when it has sufficient contrast against CSP's window color and falls back to native text when none does. The labels convey the result regardless of color.

Both SDKs declare `ui.beginTransparentWindow` with an inputs argument. The renderer uses a fullscreen transparent window with `inputs=false` and holds its own offsets. CSP also declares `NoMove`, `NoBackground` and `NoInputs` for windows that accept flag arguments. Drag checks the projected body bounds at the fitted scale. The SDK provides `ui.mousePos`, `ui.mouseClicked`, `ui.mouseDoubleClicked`, `ui.mouseDown`, `ui.mouseReleased`, `ui.mouseDragDelta`, `ui.windowHovered`, `ui.itemActive` and `ui.setMouseCursor`. HaloHUD uses the pointer position relative to its initial position so it can apply its own clamp. It gives hovered ImGui windows and registered visible AC apps priority before starting a drag. CSP documents `ui.captureMouse` as suppressing the rest of AC's mouse handling. HaloHUD relies on AC/CSP making the cursor available. Camera and other-app routing still require a live check.

See [the controls checklist](TESTING.md#controls-window-checklist) and [mouse positioning tests](TESTING.md#mouse-positioning) for in-game validation.
