// Copyright (c) FIRST and other WPILib contributors.
// Open Source Software; you can modify and/or share it under the terms of
// the WPILib BSD license file in the root directory of this project.

package frc.robot.commands.swervedrive;

import edu.wpi.first.math.geometry.Rotation2d;
import edu.wpi.first.math.kinematics.SwerveModuleState;
import edu.wpi.first.wpilibj2.command.Command;

import frc.robot.subsystems.swervedrive.SwerveSubsystem;

import java.util.function.DoubleSupplier;

/**
 * Points every module at the direction of the (already sign-corrected) left stick without
 * translating the robot. This reproduces the CTR {@code SwerveRequest.PointWheelsAt} demo request.
 *
 * <p>When the stick is near center the wheels return to straight-ahead. If YAGSL's per-module
 * anti-jitter suppresses angle updates at zero speed on your bot, this is a cosmetic no-op and can
 * safely be dropped from the bindings.
 */
public class PointWheelsAt extends Command {

    private static final double STICK_DEADBAND = 0.1;

    private final SwerveSubsystem swerve;
    private final DoubleSupplier x;
    private final DoubleSupplier y;

    public PointWheelsAt(SwerveSubsystem swerve, DoubleSupplier x, DoubleSupplier y) {
        this.swerve = swerve;
        this.x = x;
        this.y = y;
        addRequirements(swerve);
    }

    @Override
    public void execute() {
        double vx = x.getAsDouble();
        double vy = y.getAsDouble();
        Rotation2d heading =
                (Math.hypot(vx, vy) < STICK_DEADBAND) ? Rotation2d.kZero : new Rotation2d(vx, vy);

        int moduleCount = swerve.getSwerveDrive().getModules().length;
        SwerveModuleState[] states = new SwerveModuleState[moduleCount];
        for (int i = 0; i < moduleCount; i++) {
            states[i] = new SwerveModuleState(0.0, heading);
        }
        swerve.getSwerveDrive().setModuleStates(states, true);
    }
}
