// Copyright (c) FIRST and other WPILib contributors.
// Open Source Software; you can modify and/or share it under the terms of
// the WPILib BSD license file in the root directory of this project.

package frc.robot;

import edu.wpi.first.math.geometry.Translation2d;
import edu.wpi.first.wpilibj.Filesystem;
import edu.wpi.first.wpilibj2.command.Command;
import edu.wpi.first.wpilibj2.command.Commands;
import edu.wpi.first.wpilibj2.command.button.CommandXboxController;
import edu.wpi.first.wpilibj2.command.button.RobotModeTriggers;

import frc.robot.Constants.OperatorConstants;
import frc.robot.commands.swervedrive.PointWheelsAt;
import frc.robot.subsystems.swervedrive.SwerveSubsystem;

import java.io.File;

import swervelib.SwerveInputStream;

/**
 * Declares the subsystems and binds the driver controls. The bindings intentionally mirror the CTR
 * Phoenix Tuner-X swerve template so the feel carries over from the Kraken bot:
 *
 * <ul>
 *   <li>Left stick = translate, right stick X = rotate (field-oriented, 10% deadband)</li>
 *   <li>A = X-lock / brake</li>
 *   <li>B = point wheels at the left-stick heading</li>
 *   <li>POV up/down = robot-relative straight nudge</li>
 *   <li>Left bumper = reset field-centric heading</li>
 *   <li>Back/Start + Y = drive/steer SysId routines</li>
 * </ul>
 */
public class RobotContainer {

    private final CommandXboxController driverXbox =
            new CommandXboxController(OperatorConstants.DRIVER_CONTROLLER_PORT);

    private final SwerveSubsystem drivebase =
            new SwerveSubsystem(new File(Filesystem.getDeployDirectory(), "swerve"));

    /**
     * Field-oriented, angular-velocity control. Left Y/X drive translation (negated for WPILib's
     * "forward = +X, left = +Y" convention); right X commands rotation rate.
     */
    private final SwerveInputStream driveAngularVelocity =
            SwerveInputStream.of(
                            drivebase.getSwerveDrive(),
                            () -> -driverXbox.getLeftY(),
                            () -> -driverXbox.getLeftX())
                    .withControllerRotationAxis(() -> -driverXbox.getRightX())
                    .deadband(OperatorConstants.DEADBAND)
                    .scaleTranslation(1.0)
                    .allianceRelativeControl(true);

    public RobotContainer() {
        configureBindings();
    }

    private void configureBindings() {
        // Default teleop command: field-oriented drive.
        drivebase.setDefaultCommand(drivebase.driveFieldOriented(driveAngularVelocity));

        // A: hold to X-lock the wheels (CTR SwerveDriveBrake).
        driverXbox.a().whileTrue(Commands.runOnce(drivebase::lock, drivebase).repeatedly());

        // B: point wheels at the left-stick heading (CTR PointWheelsAt).
        driverXbox
                .b()
                .whileTrue(
                        new PointWheelsAt(
                                drivebase, () -> -driverXbox.getLeftY(), () -> -driverXbox.getLeftX()));

        // POV up/down: robot-relative straight nudge (CTR forwardStraight).
        driverXbox
                .povUp()
                .whileTrue(
                        drivebase.run(
                                () ->
                                        drivebase.drive(
                                                new Translation2d(OperatorConstants.NUDGE_SPEED, 0),
                                                0,
                                                false)));
        driverXbox
                .povDown()
                .whileTrue(
                        drivebase.run(
                                () ->
                                        drivebase.drive(
                                                new Translation2d(-OperatorConstants.NUDGE_SPEED, 0),
                                                0,
                                                false)));

        // Left bumper: reset field-centric heading (CTR seedFieldCentric).
        driverXbox.leftBumper().onTrue(Commands.runOnce(drivebase::zeroGyro));

        // SysId (hold Back+Y for drive, Start+Y for steer). Run each exactly once per log.
        driverXbox.back().and(driverXbox.y()).whileTrue(drivebase.sysIdDriveMotorCommand());
        driverXbox.start().and(driverXbox.y()).whileTrue(drivebase.sysIdAngleMotorCommand());

        // Zero heading at the start of autonomous, per YAGSL guidance (gyro zeroing was removed
        // from library startup).
        RobotModeTriggers.autonomous().onTrue(Commands.runOnce(drivebase::zeroGyro));
    }

    public Command getAutonomousCommand() {
        // No paths defined yet. Build autos in PathPlanner, then return one here, e.g.:
        //   return drivebase.getSwerveDrive() != null ? new PathPlannerAuto("MyAuto") : ...;
        return Commands.print("No autonomous command configured");
    }
}
