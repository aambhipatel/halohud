# Formula Ultra 2026 — inspection and calibration status

Car folder inspected read-only:
`<Assetto Corsa>/content/cars/formula_ultra_26`

**The car has data.acd and no loose data directory. data.acd was not opened, unpacked or modified.** No original car file was changed. No third-party scripts or model assets are redistributed in this package.

The profile selects only the exact `formula_ultra_26` car ID. Readable metadata is stored in `[CAR_PROFILE_FORMULA_ULTRA_26]` in config.ini and shown in HaloHUD controls. Unknown physics quantities are marked **-1**, not filled with guessed values. Other car IDs use the generic `[HUD]` settings. Save preserves both sections; Reset previews their defaults.

## Values used and their sources

| Value | Found value | Source | Use |
|---|---|---|---|
| Name | Formula Ultra 2026 | `ui/ui_car.json`, `name` | Profile/control title. |
| Class | race | same file, `class` | Controls metadata. |
| Brand | Formula Ultra | same file, `brand` | Inspection record only. |
| UI power | 950 bhp | same file, `specs.bhp` | Profile metadata, not a physics claim. |
| UI torque | 575Nm | same file, `specs.torque` | Profile metadata. |
| UI weight | 768kg* | same file, `specs.weight` | Profile metadata; asterisk retained. |
| UI top speed | 350+km/h | same file, `specs.topspeed` | Profile metadata. |
| UI acceleration | 2s 0-100 | same file, `specs.acceleration` | Profile metadata. |
| UI power/weight | 0.81 kg/hp | same file, `specs.pwratio` | Profile metadata. |
| Display mesh | LCD | `extension/ext_config.ini`, SCRIPTABLE_DISPLAY | Profile diagnostic. |
| Active display script | SF24_Display_script.lua | same section, SCRIPT | Diagnostic; no script edited. |
| Display origin in its texture | 0,0 | same section, DISPLAY_POS | Texture coordinates only, not a world position. |
| Battery readout | `kersCharge * 100` | `extension/src/display_helper.lua`, drawBatteryRemaining | Confirms the normalized charge source already used by HaloHUD. |
| Per-lap bar | `1-kersLoad` | same helper, drawErsBarPerLap | Distinct from battery charge/recovery; not substituted. |
| DRS indication | `car.drsAvailable`, `car.drsActive` | `extension/SF24_LEDs_script.lua` | Supports standard CSP DRS as the Active Aero proxy. |
| DRS race-control integration | RAREDATA drsEnabled/drsAvailable | `extension/src/connection.lua` and helper | Observed optional race-control channel; not assumed to represent physical wing angle. |
| RPM limiter | **not exported** | `data/engine.ini` is packed | Static profile -1. During a live session, use verified `car.rpmLimiter` if positive. |
| Idle / physics power LUT | **not exported** | engine.ini and referenced LUTs packed | No idle or power-curve physics value invented. |
| Gear count | **not exported** | drivetrain.ini packed | Static profile -1; use live `car.gearCount` when physics is available. |
| ERS capacity/recovery/deploy calibration | **not exported** | ers.ini/kers.ini packed | Capacity remains -1; recovery uses the generic configurable fraction/sec rate, explicitly uncalibrated. |
| Physical DRS triggers / custom aero | **not exported** | drs.ini/controllers packed | Standard live DRS flags only; no custom aero state guessed. |
| Camera position / FOV / pitch | **not exported** | cameras.ini and car.ini packed | No working car-specific camera asserted. |

The UI graph ends at **13,050 RPM**, and the LED script uses thresholds including **11,800 RPM**. These are graph/LED values, **not verified engine limiter values**. They are not used to set the limiter or scale. The 950 bhp UI text also need not equal the physics LUT's peak. The profile's runtime scale and limiter diagnostic come from the actual CSP limiter, not these UI numbers.

## Model inspection

The supplied OBJ template was parsed as geometry. `body_halo` bounds in its own exported coordinates are:

`min=(-0.347467, 0.697204, -0.051851)`
`max=(0.347467, 0.899162, 0.841194)`

It contains no named LCD, driver-head or steering-wheel object. These template bounds alone do not locate the camera optical center or driver eyes.

The actual `fu26.kn5` was also read using the public Content Manager KN5 layout, skipping texture payloads and reading the node hierarchy/vertices without exporting model assets. It contains `STEER_HR/LCD`, `body_halo`, and a mesh named `cameras`. Parsed bind-pose bounds are recorded in `model-inspection.json`. In the parsed hierarchy, the LCD mesh bounds are approximately:

`min=(-0.082658, 0.585381, 0.432789)`
`max=(0.082709, 0.717296, 0.505859)`

The parsed halo bounds are approximately:

`min=(-0.377363, 0.666762, -0.082293)`
`max=(0.376235, 0.929604, 0.871438)`

These are **derived bind-pose model coordinates**, not projected HUD positions. The KN5 contains trailing data not interpreted by the inspection script, and its bounds differ from the OBJ template. The parsed root contains no driver/head node. The `cameras` mesh is geometry, not an exported cameras.ini view. Those limitations, the unavailable car.ini model/driver offsets, and camera transforms prevent a verified optical placement or steering-display screen exclusion rectangle. No guessed projection/clearance is installed. The generic DEMO label remains small and above the HUD dial.

The reader layout was checked against [Content Manager's Kn5Basic reader](https://github.com/gro-ove/actools/blob/master/AcTools/Kn5File/Kn5Basic.cs) and [binary reader](https://github.com/gro-ove/actools/blob/master/AcTools/ReadAheadBinaryReader.cs). The Python reader rejects non-KN5 inputs and never touches data.acd. `car-inspection.json` records hashes/sizes of readable metadata/scripts and OBJ bounds; `model-inspection.json` records parsed model findings and the unparsed trailing-byte count.

## Exactly what to export to finish the calibration

Provide an already-authorized **loose-file export**, without changing the installed car:

1. `data/engine.ini`, the referenced power/torque/coast LUTs and any engine-controller INIs/LUTs.
2. `data/drivetrain.ini`.
3. `data/ers.ini` and/or `data/kers.ini` if present, plus every LUT/controller they reference. If absent, explicitly confirm that rather than creating one.
4. `data/drs.ini`, plus `data/wings.ini`, `data/ctrl_wing*.ini` and referenced LUTs if the car uses custom active aero.
5. `data/cameras.ini` and `data/car.ini`.
6. For confirmed screen clearance: an exported in-car camera transform (position, forward, up, FOV), and the driver head/eye transform in the same car coordinate system. A showroom node-transform export of `LCD`, `STEER_HR`, `body_halo` and the head/eye reference will resolve the model/template coordinate mismatch. The full model need not be uploaded again; it is already accessible.

If no loose-file export is available, keep the live-CSP powertrain adaptation and generic recovery calibration. This package deliberately does not use `INIConfig.carData()` as a way to read the packed physics around your instruction.

`camera/formula_ultra_26.cameras.ini.example` is a separate **comment-only merge guide** pending those exports. The existing generic camera example is explicitly illustrative and must not be mistaken for a calibrated Formula Ultra camera. A working car-specific position/FOV/pitch cannot be supplied honestly from the presently readable evidence.

Version 1.4 uses a fixed visual red threshold above 11,000 RPM as requested. Profile limiter values still determine scale/diagnostics but do not override that visual rule.
