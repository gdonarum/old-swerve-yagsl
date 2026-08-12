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
