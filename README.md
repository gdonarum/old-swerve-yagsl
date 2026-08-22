# old-swerve-yagsl

YAGSL swerve drive for the **old West Coast swerve robot** (NEO motors on Spark Max, CTRE
CANcoders, Studica **navX3** over CAN). This is the vendor-appropriate counterpart to the
Kraken/Phoenix 6 `ctr-swerve-test` project — it reproduces the same driver commands we liked in the
CTR Tuner-X template, but on the stack that matches this robot's hardware.

Driver controls are documented in [CONTROLS.md](CONTROLS.md).

## Hardware

| Robot part | Device | YAGSL config (`type`) |
|---|---|---|
| Drive motors (x4) | NEO on Spark Max | `sparkmax` |
| Steer motors (x4) | NEO on Spark Max | `sparkmax` |
| Azimuth encoders (x4) | CTRE CANcoder | `cancoder` |
| Heading sensor | Studica navX3 (CAN) | `navx3` |

All values below are carried over from last season's config (`frc7770/robot-2026`).

### CAN IDs / module offsets

| Module | Drive | Steer | CANcoder | Abs offset (deg) | Location (front, left) in |
|---|---|---|---|---|---|
| Front Left | 24 | 32 | 4 | 118.783 | (10.3125, 9.0652) |
| Front Right | 26 | 27 | 1 | 217.969 | (10.3125, -9.0652) |
| Back Left | 29 | 22 | 2 | 283.096 | (-10.3125, 9.0652) |
| Back Right | 25 | 23 | 3 | 98.216 | (-10.3125, -9.0652) |

navX3 is CAN id **63**, `invertedIMU: true`. Drive and steer are both inverted on every module.

### Geometry & tuning (`deploy/swerve/modules/*.json`)

- Drive reduction **6.55:1**, steer reduction **10.28:1**, **4in** wheels
- Current limits: drive **40 A**, steer **20 A**; ramp **0.25 s**; wheel COF **1.19**
- Drive PIDF `p=0.07 i=0.001 d=0.01`; steer PIDF `p=0.0072 i=5e-7 d=0.028`
- `MAX_SPEED` in `Constants.java` ≈ **4.6 m/s** (NEO free speed through 6.55:1 on 4in wheels)

## Driver command parity with the CTR project

| CTR Phoenix request | Button | YAGSL implementation |
|---|---|---|
| `FieldCentric` (default) | Left/right sticks | `SwerveInputStream` → `driveFieldOriented` |
| `SwerveDriveBrake` | A | `SwerveSubsystem.lock()` (`lockPose`) |
| `PointWheelsAt` | B | `commands/swervedrive/PointWheelsAt` |
| `RobotCentric` nudge | POV up/down | `drive(Translation2d, 0, fieldRelative=false)` |
| `seedFieldCentric` | Left bumper | `SwerveSubsystem.zeroGyro()` |
| SysId routines | Back/Start + Y | `sysIdDriveMotorCommand` / `sysIdAngleMotorCommand` |
| `registerTelemetry` | — | Built into YAGSL (`SwerveDriveTelemetry`) |

## Alternative heading sensor: CTRE Pigeon (gen 1 / "Pigeon 1.1")

The gyro is fully JSON-driven — `SwerveSubsystem` just runs `SwerveParser`, so swapping the
heading sensor is a config + vendordep change, no Java edits. Support for the original CTRE
**Pigeon IMU** (the gen-1 "Pigeon 1.1", *not* the Pigeon 2.0) is wired up here.

**Why a vendordep was needed.** YAGSL's `"pigeon"` gyro type maps to `swervelib.imu.PigeonSwerve`,
which wraps `com.ctre.phoenix.sensors.WPI_PigeonIMU`. The gen-1 Pigeon is a **Phoenix 5**-only
device (Pigeon 2.0 moved to Phoenix 6; the gen-1 never did). This project ships **Phoenix 6** for
the CANcoders but had no Phoenix 5, so selecting `"pigeon"` would compile fine and then throw
`NoClassDefFoundError: .../WPI_PigeonIMU` the moment `SwerveParser` built the drive. The fix is the
added **`vendordeps/Phoenix5-frc2026-latest.json`** (v5.36.0). Phoenix 5 declares Phoenix 6 as a
prerequisite, and the two coexist fine — only the Phoenix *replay* variants conflict.

**To actually run the Pigeon**, edit `src/main/deploy/swerve/swervedrive.json` — replace the `imu`
block (currently navX3) with:

```json
  "imu": {
    "type": "pigeon",
    "id": 0,
    "canbus": null
  },
```

- `id` → the Pigeon's CAN id in **Phoenix Tuner v5**. **`0` above is a placeholder — set it to your
  device's real id.** (Not the navX3's `63`; give the Pigeon its own id.)
- `canbus` is ignored for the `"pigeon"` type (it's a plain CAN device, not CANivore/`canbus`-aware),
  so leave it `null`.
- Re-check **`invertedIMU`**: keep it `true` only if it makes CCW-positive when the robot turns left.
  The gen-1 Pigeon reports CW-positive when mounted label-up, so with a flat, label-up mount you will
  likely need `"invertedIMU": false` here — verify on the field and flip if heading runs backwards.
- The gen-1 Pigeon **self-calibrates its gyro at boot and must sit still** for a few seconds after
  power-up; field-calibrate the accelerometer/compass once in Phoenix Tuner v5. Mount it flat and as
  close to the robot's center of rotation as practical.

> Wired instead through a TalonSRX's gadgeteer ribbon cable? Use `"type": "pigeon_via_talonsrx"`
> with `id` set to the **host TalonSRX's** CAN id. This robot uses the direct-CAN wiring above.

`Phoenix6-frc2026-latest.json` and `Phoenix5-frc2026-latest.json` must both stay installed while the
Pigeon is in use (VS Code → *WPILib: Manage Vendor Libraries* will show both). If you later revert to
the navX3, the Phoenix 5 dep is harmless to leave in place.

## First-run checklist

1. Open in VS Code (WPILib 2026) and let it import vendordeps, or run `./gradlew build`.
2. **navX3:** install **StudicaLib** only (not the legacy `Studica` vendordep), firmware ≥ 5.0.4,
   confirm the CAN id (63) in Studica Hardware Manager.
3. Verify each module's `absoluteEncoderOffset` — re-zero in YAGSL if wheels don't point forward.
4. Confirm drive/steer inversion and CANcoder ids match the physical bot before driving.
5. `MAX_SPEED` and the PathPlanner `settings.json` mass/MOI are estimates — refine after SysId.

## Layout

```
src/main/deploy/swerve/           YAGSL config (swervedrive.json, controllerproperties.json)
src/main/deploy/swerve/modules/   per-module + physical/pidf properties
src/main/java/frc/robot/          Robot, RobotContainer, Constants
  subsystems/swervedrive/         SwerveSubsystem (YAGSL wrapper)
  commands/swervedrive/           PointWheelsAt
```
