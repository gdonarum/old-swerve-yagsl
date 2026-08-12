# Driver controls

Single Xbox controller on port 0. Field-oriented unless noted.

| Input | Action |
|---|---|
| **Left stick** | Translate (up = away from driver, left = to driver's left) |
| **Right stick X** | Rotate (angular velocity) |
| **A (hold)** | X-lock the wheels — brake / resist pushing |
| **B (hold)** | Point all wheels at the left-stick heading (no translation) |
| **POV up (hold)** | Robot-relative nudge forward at 0.5 m/s |
| **POV down (hold)** | Robot-relative nudge backward at 0.5 m/s |
| **Left bumper** | Reset field-centric heading (zero the gyro) |
| **Back + Y (hold)** | Drive-motor SysId routine |
| **Start + Y (hold)** | Steer-motor SysId routine |

Notes:
- A 10% deadband is applied to translation and rotation.
- Run each SysId routine exactly once per log, then analyze with the WPILib SysId tool.
- Heading is auto-zeroed at the start of autonomous (YAGSL no longer zeros the gyro on startup).
