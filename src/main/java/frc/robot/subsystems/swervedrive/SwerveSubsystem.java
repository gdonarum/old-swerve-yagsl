// Copyright (c) FIRST and other WPILib contributors.
// Open Source Software; you can modify and/or share it under the terms of
// the WPILib BSD license file in the root directory of this project.

package frc.robot.subsystems.swervedrive;

import com.pathplanner.lib.auto.AutoBuilder;
import com.pathplanner.lib.config.PIDConstants;
import com.pathplanner.lib.config.RobotConfig;
import com.pathplanner.lib.controllers.PPHolonomicDriveController;

import edu.wpi.first.math.geometry.Pose2d;
import edu.wpi.first.math.geometry.Rotation2d;
import edu.wpi.first.math.geometry.Translation2d;
import edu.wpi.first.math.kinematics.ChassisSpeeds;
import edu.wpi.first.wpilibj.DriverStation;
import edu.wpi.first.wpilibj2.command.Command;
import edu.wpi.first.wpilibj2.command.SubsystemBase;
import edu.wpi.first.wpilibj2.command.sysid.SysIdRoutine.Config;

import frc.robot.Constants;

import java.io.File;
import java.util.function.Supplier;

import swervelib.SwerveDrive;
import swervelib.SwerveDriveTest;
import swervelib.parser.SwerveParser;
import swervelib.telemetry.SwerveDriveTelemetry;
import swervelib.telemetry.SwerveDriveTelemetry.TelemetryVerbosity;

/**
 * A thin command-based wrapper around a YAGSL {@link SwerveDrive}. It loads the JSON config from
 * {@code src/main/deploy/swerve} and exposes the drive/utility methods used by
 * {@link frc.robot.RobotContainer} to reproduce the CTR Tuner-X driver commands.
 */
public class SwerveSubsystem extends SubsystemBase {

    private final SwerveDrive swerveDrive;

    /**
     * @param directory the deploy sub-directory holding the YAGSL config (e.g. {@code swerve}).
     */
    public SwerveSubsystem(File directory) {
        SwerveDriveTelemetry.verbosity =
                Constants.COMPETITION_MODE ? TelemetryVerbosity.LOW : TelemetryVerbosity.HIGH;
        try {
            swerveDrive = new SwerveParser(directory).createSwerveDrive(Constants.MAX_SPEED);
        } catch (Exception e) {
            throw new RuntimeException("Failed to build SwerveDrive from " + directory, e);
        }

        // Match the tuning posture of the YAGSL example: let the module PID hold heading rather
        // than layering a heading-correction PID on top, and skip cosine compensation.
        swerveDrive.setHeadingCorrection(false);
        swerveDrive.setCosineCompensator(false);
        swerveDrive.setAngularVelocityCompensation(true, true, 0.1);
        swerveDrive.setModuleEncoderAutoSynchronize(false, 1);

        setupPathPlanner();
    }

    @Override
    public void periodic() {}

    public SwerveDrive getSwerveDrive() {
        return swerveDrive;
    }

    // ------------------------------------------------------------------
    // Drive commands
    // ------------------------------------------------------------------

    /**
     * Field-oriented drive from a {@link ChassisSpeeds} supplier (typically a
     * {@code SwerveInputStream}). This is the default teleop command.
     */
    public Command driveFieldOriented(Supplier<ChassisSpeeds> velocity) {
        return run(() -> swerveDrive.driveFieldOriented(velocity.get()));
    }

    /** Direct drive helper. {@code fieldRelative == false} gives robot-centric motion. */
    public void drive(Translation2d translation, double rotation, boolean fieldRelative) {
        swerveDrive.drive(translation, rotation, fieldRelative, false);
    }

    /** Point the modules into an X to resist being pushed (CTR SwerveDriveBrake). */
    public void lock() {
        swerveDrive.lockPose();
    }

    /** Zero the gyro / reset field-centric heading (CTR seedFieldCentric). */
    public void zeroGyro() {
        swerveDrive.zeroGyro();
    }

    public Pose2d getPose() {
        return swerveDrive.getPose();
    }

    public Rotation2d getHeading() {
        return getPose().getRotation();
    }

    public ChassisSpeeds getRobotVelocity() {
        return swerveDrive.getRobotVelocity();
    }

    public void resetOdometry(Pose2d pose) {
        swerveDrive.resetOdometry(pose);
    }

    // ------------------------------------------------------------------
    // SysId (system identification) routines
    // ------------------------------------------------------------------

    public Command sysIdDriveMotorCommand() {
        return SwerveDriveTest.generateSysIdCommand(
                SwerveDriveTest.setDriveSysIdRoutine(new Config(), this, swerveDrive, 12, true),
                3.0, 5.0, 3.0);
    }

    public Command sysIdAngleMotorCommand() {
        return SwerveDriveTest.generateSysIdCommand(
                SwerveDriveTest.setAngleSysIdRoutine(new Config(), this, swerveDrive),
                3.0, 5.0, 3.0);
    }

    // ------------------------------------------------------------------
    // PathPlanner
    // ------------------------------------------------------------------

    /**
     * Wire the drivetrain into PathPlanner's {@code AutoBuilder}. The robot config is read from
     * {@code src/main/deploy/pathplanner/settings.json}; if that fails we log and continue so the
     * robot is still drivable in teleop.
     */
    private void setupPathPlanner() {
        try {
            RobotConfig config = RobotConfig.fromGUISettings();
            AutoBuilder.configure(
                    this::getPose,
                    this::resetOdometry,
                    this::getRobotVelocity,
                    (speedsRobotRelative, moduleFeedForwards) ->
                            swerveDrive.setChassisSpeeds(speedsRobotRelative),
                    new PPHolonomicDriveController(
                            new PIDConstants(5.0, 0.0, 0.0),
                            new PIDConstants(5.0, 0.0, 0.0)),
                    config,
                    () -> {
                        var alliance = DriverStation.getAlliance();
                        return alliance.isPresent() && alliance.get() == DriverStation.Alliance.Red;
                    },
                    this);
        } catch (Exception e) {
            DriverStation.reportError(
                    "PathPlanner failed to initialize: " + e.getMessage(), e.getStackTrace());
        }
    }
}
