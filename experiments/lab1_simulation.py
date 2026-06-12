#!/usr/bin/env python3
"""MATE381 Lab 1 — K-Type Thermocouple & SSR Tube Furnace Simulation.

Physics-based simulation of:
  Part 2: Cold junction temperature comparison (room temp vs 0°C ice bath)
  Part 3: SSR on/off temperature control with thermal inertia

Uses NIST ITS-90 standard polynomial coefficients for Type K thermocouples
(Nickel-Chromium vs Nickel-Aluminium).
"""

import csv
import os
import math

import matplotlib
matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ===================================================================
#   K-Type Thermocouple: NIST ITS-90 Polynomial Model
# ===================================================================
#
# The thermoelectric voltage E(T) for a Type K thermocouple with its
# reference junction at 0°C is given by:
#
#   E(T) = Σ_{i=0}^{n} c_i · T^i  +  a₀ · exp[ a₁ · (T − a₂)² ]
#
# Two coefficient sets cover different temperature ranges.
# We use the 0°C to +1372°C set (relevant for tube furnace work).
# -------------------------------------------------------------------
# Coefficients for T ∈ [0 °C, +1372 °C]  (E in mV)
C_HIGH = [
    -0.176004136860e-01,   # c0
     0.389212049750e-01,   # c1
     0.185587700320e-04,   # c2
    -0.994575928740e-07,   # c3
     0.318409457190e-09,   # c4
    -0.560728448890e-12,   # c5
     0.560750590590e-15,   # c6
    -0.320207200030e-18,   # c7
     0.971511471520e-22,   # c8
    -0.121047212750e-25,   # c9
]

# Exponential correction term for T ≥ 0°C
A0 = 0.118597600000e+00  # a₀
A1 = -0.118343200000e-03  # a₁
A2 = 0.126968600000e+03  # a₂


def thermocouple_emf_mv(T_C):
    """Compute K-type thermocouple EMF (mV) with reference junction at 0°C.

    Uses standard NIST ITS-90 polynomial + exponential correction.

    Args:
        T_C: Temperature in °C.

    Returns:
        EMF in millivolts.
    """
    if T_C < 0:
        # For negative temperatures a separate coefficient set exists;
        # the experiment only involves positive temperatures, so we
        # approximate the low-end behaviour linearly with ~39.5 µV/°C.
        return 0.0395 * T_C

    poly = sum(c * (T_C ** i) for i, c in enumerate(C_HIGH))
    exp_term = A0 * math.exp(A1 * (T_C - A2) ** 2)
    return poly + exp_term


def measured_voltage(T_hot, T_cold):
    """Net voltage measured by DAQ when cold junction is at T_cold.

    Seebeck effect:  V_meas = E(T_hot) - E(T_cold)

    The thermocouple generates an EMF proportional to the temperature
    *difference* between its hot and cold junctions.  If the cold
    junction is NOT at 0°C, the apparent voltage at the DAQ terminals
    is reduced by the EMF the cold junction itself generates.
    """
    return thermocouple_emf_mv(T_hot) - thermocouple_emf_mv(T_cold)


# ===================================================================
#   Part 2: Cold Junction Comparison
# ===================================================================

def simulate_cold_junction_comparison():
    """Generate two voltage-temperature sweeps:

    Run 1: cold junction at 25°C (room temperature)
    Run 2: cold junction at  0°C (ice-water bath)

    Both runs sweep the same hot-junction temperatures (30 → 400 °C).
    In the real experiment the second run was performed during cool-down
    from 400 °C; the physics is identical — only the cold-junction
    temperature differs.
    """
    T_hot = np.linspace(30, 400, 50)  # 50 data points
    T_cold_room = 25.0   # room temperature
    T_cold_ice = 0.0     # ice-water mixture

    V_room = np.array([measured_voltage(t, T_cold_room) for t in T_hot])
    V_ice = np.array([measured_voltage(t, T_cold_ice) for t in T_hot])

    # ----------------------------------------------------------------
    # Simulate DAQ "per-packet averaging" noise reduction
    # (900 samples/packet @ 1 kHz → averaged → ±2 µV residual noise)
    # ----------------------------------------------------------------
    rng = np.random.default_rng(42)
    noise_amplitude = 0.002  # mV  (2 µV)
    V_room += rng.normal(0, noise_amplitude, len(V_room))
    V_ice  += rng.normal(0, noise_amplitude, len(V_ice))

    return T_hot, V_room, V_ice, T_cold_room, T_cold_ice


# ===================================================================
#   Part 3: SSR On/Off Temperature Control
# ===================================================================

def simulate_ssr_control(setpoint=400.0, deadband=5.0, duration_s=600):
    """Simulate bang-bang (on/off) furnace temperature control.

    The SSR is driven by a digital comparison:
        if T_measured < (setpoint - deadband)  →  AO0 = 5 V  →  SSR ON
        if T_measured > (setpoint + deadband)  →  AO0 = 0 V  →  SSR OFF

    Tube furnace thermal dynamics are modelled as a first-order
    plus dead-time (FOPDT) process:

        τ · dT/dt + T = K_p · u(t − θ)

    where at steady state with u=1, T → K_p.
    K_p represents the maximum furnace temperature when
    the heater is continuously energised.

    Parameters:
        τ       time constant (thermal inertia), seconds
        K_p     process static gain (max attainable temperature), °C
        θ       dead time (transport / sensor lag), seconds
        u(t)    1 = SSR ON (heating), 0 = SSR OFF (cooling)
    """
    dt = 0.5               # 0.5-second time step for smooth oscillation
    steps = int(duration_s / dt)
    time = np.arange(0, duration_s, dt)

    # FOPDT parameters for a small tube furnace
    tau = 130.0            # time constant, seconds (larger → more inertia)
    K_p = 460.0            # max furnace temperature when SSR ON continuously, °C
    theta_steps = int(2.0 / dt)  # dead time ≈ 2 seconds

    # Cooling is via natural convection/radiation (slower than heating)
    tau_cool = 190.0       # longer time constant for passive cooling

    T = np.zeros(steps)
    T[0] = 25.0            # start at ambient
    ssr_state = np.zeros(steps, dtype=int)
    rng = np.random.default_rng(42)

    for i in range(1, steps):
        # Bang-bang controller with hysteresis deadband
        if T[i - 1] < (setpoint - deadband):
            ssr_state[i] = 1   # turn ON
        elif T[i - 1] > (setpoint + deadband):
            ssr_state[i] = 0   # turn OFF
        else:
            ssr_state[i] = ssr_state[i - 1]  # hold previous state

        # FOPDT with delayed input
        idx_delayed = max(0, i - theta_steps)
        heater = ssr_state[idx_delayed]

        if heater == 1:
            # Heating phase: drives T toward K_p
            dTdt = (K_p - T[i - 1]) / tau
        else:
            # Cooling phase: drives T toward ambient (25 °C)
            dTdt = (25.0 - T[i - 1]) / tau_cool

        T[i] = T[i - 1] + dTdt * dt

        # Small random sensor noise (±0.2 °C)
        T[i] += rng.normal(0, 0.2)

    # SSR control voltage (0 or 5 V)
    V_control = ssr_state * 5.0

    return time, T, V_control, setpoint, deadband


# ===================================================================
#   Data Export
# ===================================================================

def save_csv(filename, columns, headers):
    """Save simulation data as CSV."""
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in zip(*columns):
            writer.writerow([f"{v:.4f}" if isinstance(v, float) else str(v) for v in row])
    print(f"  Saved: {path} ({len(columns[0])} rows)")


# ===================================================================
#   Plotting
# ===================================================================

def plot_cold_junction_comparison(T_hot, V_room, V_ice, T_cold_room, T_cold_ice):
    """Figure 1: Voltage vs Temperature for two cold-junction conditions."""
    fig, ax = plt.subplots(figsize=(8, 5.5))

    ax.plot(T_hot, V_ice, "b-", linewidth=1.5, label=f"Cold Junction at {T_cold_ice:.0f} °C (Ice Bath)")
    ax.plot(T_hot, V_room, "r--", linewidth=1.5, label=f"Cold Junction at {T_cold_room:.0f} °C (Room Temp)")

    ax.set_xlabel("Hot-Junction Temperature (°C)", fontsize=12)
    ax.set_ylabel("Measured Voltage (mV)", fontsize=12)
    ax.set_title("K-Type Thermocouple Output: Cold Junction Comparison", fontsize=13)
    ax.legend(fontsize=10, loc="upper left")
    ax.grid(True, alpha=0.3)

    # Annotate the voltage difference at a representative temperature
    idx_300 = np.argmin(np.abs(T_hot - 300))
    dv = V_ice[idx_300] - V_room[idx_300]
    ax.annotate(
        f"ΔV ≈ {dv:.3f} mV\nat T_hot = 300 °C",
        xy=(T_hot[idx_300], V_ice[idx_300]),
        xytext=(T_hot[idx_300] - 80, V_ice[idx_300] + 1.5),
        arrowprops=dict(arrowstyle="->", color="gray"),
        fontsize=9, color="navy",
    )

    plt.tight_layout()
    path = os.path.join(OUT_DIR, "fig1_cold_junction_comparison.png")
    fig.savefig(path, dpi=150)
    print(f"  Saved: {path}")
    plt.close(fig)


def plot_ssr_control(time, T, V_control, setpoint, deadband):
    """Figure 2: SSR bang-bang control — temperature vs time."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1]})

    # Top panel: temperature
    ax1.plot(time, T, "b-", linewidth=0.8, label="Measured Temperature")
    ax1.axhline(y=setpoint, color="k", linestyle=":", alpha=0.6,
                label=f"Setpoint = {setpoint} °C")
    ax1.axhline(y=setpoint + deadband, color="r", linestyle="--", alpha=0.4,
                label=f"±{deadband} °C Deadband")
    ax1.axhline(y=setpoint - deadband, color="r", linestyle="--", alpha=0.4)
    ax1.set_ylabel("Temperature (°C)", fontsize=12)
    ax1.set_title("SSR On/Off Tube Furnace Temperature Control", fontsize=13)
    ax1.legend(fontsize=9, loc="upper left")
    ax1.grid(True, alpha=0.3)

    # Bottom panel: SSR control voltage
    ax2.step(time, V_control, "g-", where="post", linewidth=1.2)
    ax2.set_xlabel("Time (s)", fontsize=12)
    ax2.set_ylabel("SSR Control\nVoltage (V)", fontsize=12)
    ax2.set_ylim(-0.5, 6)
    ax2.set_yticks([0, 5])
    ax2.set_yticklabels(["0 V (OFF)", "5 V (ON)"])
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, "fig2_ssr_control.png")
    fig.savefig(path, dpi=150)
    print(f"  Saved: {path}")
    plt.close(fig)


# ===================================================================
#   Main
# ===================================================================

def main():
    print("=" * 60)
    print("MATE381 Lab 1 — Physics Simulation")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Part 2: Cold junction comparison
    # ------------------------------------------------------------------
    print("\n[Part 2] Cold Junction Temperature Comparison")
    print("-" * 40)
    T_hot, V_room, V_ice, T_cold_room, T_cold_ice = \
        simulate_cold_junction_comparison()

    save_csv(
        "lab1_cold_junction_comparison.csv",
        [T_hot, V_room, V_ice],
        ["Hot_Junction_Temperature_C", "Voltage_mV_ColdJunction_25C",
         "Voltage_mV_ColdJunction_0C"],
    )

    plot_cold_junction_comparison(T_hot, V_room, V_ice, T_cold_room, T_cold_ice)

    # Quick sanity check
    dv_max = np.max(V_ice - V_room)
    print(f"  Max voltage difference (0°C - 25°C cold junction): {dv_max:.4f} mV")
    print(f"  Cold junction at 0°C always yields HIGHER voltage: "
          f"{'PASS' if np.all(V_ice > V_room) else 'FAIL'}")

    # ------------------------------------------------------------------
    # Part 3: SSR on/off temperature control
    # ------------------------------------------------------------------
    print("\n[Part 3] SSR On/Off Temperature Control")
    print("-" * 40)
    setpoint = 400.0
    deadband = 5.0
    duration = 600  # total simulation time, seconds
    time, T, V_control, sp, db = simulate_ssr_control(
        setpoint=setpoint, deadband=deadband, duration_s=duration
    )

    # Focus on steady-state region (second half of simulation)
    ss_mask = time > (duration / 2)
    T_ss = T[ss_mask]
    T_min, T_max = T_ss.min(), T_ss.max()

    save_csv(
        "lab1_ssr_control.csv",
        [time, T, V_control],
        ["Time_s", "Temperature_C", "SSR_Control_Voltage_V"],
    )

    plot_ssr_control(time, T, V_control, sp, db)

    print(f"  Steady-state temperature range: {T_min:.1f} – {T_max:.1f} °C")
    print(f"  Setpoint: {sp} °C, deadband: ±{db} °C")
    print(f"  Thermal inertia overshoot beyond deadband: "
          f"lower={sp - db - T_min:+.1f} °C, upper={T_max - sp - db:+.1f} °C")

    print(f"\nAll outputs written to: {OUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
