import numpy as np
import pandas as pd

# Simulation parameters
fs = 1000        # Sampling frequency in Hz
t_end = 1.0      # Total time in seconds
f_sine = 5       # Frequency of sine wave in Hz
amplitude = 1.0  # Amplitude of sine wave

# Time vector
time = np.linspace(0, t_end, int(fs*t_end))

# Example waveforms
V1 = amplitude * np.sin(2 * np.pi * f_sine * time)
V2 = 0.5 * amplitude * np.sin(2 * np.pi * 2*f_sine * time + np.pi/4)  # Another sine wave

# Create DataFrame
df = pd.DataFrame({
    "Time": time,
    "V1": V1,
    "V2": V2
})

# Save CSV
df.to_csv("example_waveform.csv", index=False)
print("Example waveform saved as 'example_waveform.csv'")
