import subprocess
import os

# Output path
output_file = r"C:\ai_bot_temp\test_tone.wav"

# Make sure the folder exists
os.makedirs(os.path.dirname(output_file), exist_ok=True)

print(f"Generating test audio file at: {output_file}")

# FFmpeg command: generate a 3-second sine wave at 440 Hz
cmd = [
    "ffmpeg",
    "-f", "lavfi",
    "-i", "sine=frequency=440:duration=3",
    "-c:a", "pcm_s16le",  # WAV format
    output_file,
    "-y"  # overwrite if file exists
]

result = subprocess.run(cmd, capture_output=True, text=True)

print("\n--- FFmpeg Output ---")
print(result.stdout)
print(result.stderr)
print("--- End of Output ---")

# Check result
if os.path.exists(output_file):
    print(f"\n✅ Success! Test audio file created: {output_file}")
else:
    print("\n❌ FFmpeg failed. See errors above.")
