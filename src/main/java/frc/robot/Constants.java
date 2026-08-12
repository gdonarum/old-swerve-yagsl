// Copyright (c) FIRST and other WPILib contributors.
// Open Source Software; you can modify and/or share it under the terms of
// the WPILib BSD license file in the root directory of this project.

package frc.robot;

import edu.wpi.first.math.util.Units;

/**
 * Project-wide constants for the NEO / West Coast swerve robot running on YAGSL.
 */
public final class Constants {

    private Constants() {}

    /** Set true at competitions to reduce telemetry/logging overhead. */
    public static final boolean COMPETITION_MODE = false;

    /**
     * Maximum attainable module (translational) speed, in meters/second. YAGSL uses this to
     * scale joystick input and to desaturate module speeds.
     *
     * <p>NEO free speed ~5676 RPM through the 6.55:1 drive reduction on a 4in (0.1016m) wheel:
     * (5676/60)/6.55 * (pi * 0.1016) ~= 4.6 m/s. 15.1 ft/s ~= 4.6 m/s.
     */
    public static final double MAX_SPEED = Units.feetToMeters(15.1);

    public static final class OperatorConstants {
        public static final int DRIVER_CONTROLLER_PORT = 0;
        /** Translation/rotation joystick deadband (matches the CTR project's 10%). */
        public static final double DEADBAND = 0.1;
        /** Speed of the POV robot-relative nudge, in meters/second. */
        public static final double NUDGE_SPEED = 0.5;
    }
}
