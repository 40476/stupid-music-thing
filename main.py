#!/usr/bin/env python3
"""
So um yea i got bored, made this, and had gemini add comments
just enjoy it idk what to do with this thing
"""

import argparse
import math
import random
import wave
import struct
import sys
import os
import concurrent.futures

# -----------------------------------------------------------------------------
# Core Music Math
# -----------------------------------------------------------------------------

def get_freq(key):
    """
    Standard MIDI-style frequency calculation.
    Key 49 corresponds to 440 Hz (A4).
    """
    return 440.0 * (2.0 ** ((key - 49.0) / 12.0))

# -----------------------------------------------------------------------------
# Instrument Generators
# -----------------------------------------------------------------------------

def piano_gen(t, key, s, e, sample_rate, fix_pitch):
    """
    The "Piano" instrument (acts more like a sawtooth wave).
    """
    freq = get_freq(key)
    
    # The original JS used the frequency as the period size (t % freq).
    # We replicate that quirky math by default, or use accurate math if fixed.
    period = (sample_rate / freq) if fix_pitch else freq
    if period <= 0: return 0
    
    vol = max(0.0, 1.0 - (t - s) / (e - s)) ** 0.25
    return ((t % period) / period) * vol

def sinwave_gen(t, key, s, e, sample_rate, fix_pitch):
    """
    The "SinWave" instrument (sounds somewhat like marimba or strings).
    """
    if fix_pitch:
        freq = get_freq(key)
    else:
        # Original JS Quirky Pitch Inversion: GetFreq((1-p)*88-3.75)
        freq = get_freq(88.0 - key - 3.75)
        
    vol = max(0.0, 1.0 - (t - s) / (e - s)) ** 1.0
    
    if fix_pitch:
        phase = 2.0 * math.pi * t * freq / sample_rate
    else:
        # Original phase calculation
        phase = (((t * freq) % sample_rate) / sample_rate) * math.pi * 2.0
        
    return math.sin(phase) * vol

def noise_gen(t, key, s, e, sample_rate, fix_pitch):
    """
    The "Noise" instrument (used for drums/percussion).
    """
    if fix_pitch:
        freq = get_freq(key)
        period = sample_rate / freq
    else:
        # Original JS Quirky Pitch Inversion: GetFreq((1-p)*88+12)
        freq = get_freq(88.0 - key + 12.0)
        period = freq

    if period <= 0: return 0

    vol = max(0.0, 1.0 - (t - s) / (e - s)) ** 2.0
    
    # It multiplies white noise by a sawtooth envelope based on the pitch
    timbre = 0.5 + 0.5 * ((t % period) / period)
    return random.random() * vol * timbre

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

class Instrument:
    def __init__(self, name, generator_func):
        self.name = name
        self.generator = generator_func

class Note:
    def __init__(self, channel, key, start, end, vol=1.0):
        self.channel = channel
        self.key = key
        self.start = start
        self.end = end
        self.vol = vol

class Channel:
    def __init__(self, c_id, instrument):
        self.id = c_id
        self.instrument = instrument
        self.notes = []

class Song:
    def __init__(self, bars):
        self.bars = bars
        self.beats_per_bar = 4
        self.channels = []

# -----------------------------------------------------------------------------
# Algorithmic Composition
# -----------------------------------------------------------------------------

def compose_song(bars, seed):
    """
    Composes a song algorithmically based on the provided random seed.
    Replicates the random sequence from the original JavaScript.
    """
    if seed is not None:
        random.seed(seed)
        
    song = Song(bars)
    
    # Setup Instruments
    piano_inst = Instrument('Piano', piano_gen)
    noise_inst = Instrument('Noise', noise_gen)
    sinwave_inst = Instrument('SinWave', sinwave_gen)
    
    song.channels.append(Channel(0, piano_inst))
    song.channels.append(Channel(1, noise_inst))
    song.channels.append(Channel(2, sinwave_inst))

    # The original JS generates exactly 4 bars per sequence.
    # We will generate music in 4-bar blocks to satisfy the requested length.
    for block in range(0, bars, 4):
        base_beat = block * song.beats_per_bar
        
        # Seed variables for this block's specific progression
        v = random.randint(0, 3) - 2
        v1 = random.randint(0, 19) - 10
        v2 = random.randint(0, 19) - 10
        v3 = random.randint(0, 19) - 10
        s = 4.0
        vv = random.randint(0, 1) + 3

        ch0_notes = []
        ch1_notes = []
        ch2_notes = []

        # 1. Generate Drum Beat (First 2 bars)
        for i in range(0, 8, 2):
            offset = base_beat + float(i)
            ch1_notes.append(Note(1, 49, offset, offset + 0.125))
            ch1_notes.append(Note(1, 49, offset + 0.25, offset + 0.3125))
            ch1_notes.append(Note(1, 49, offset + 0.5, offset + 0.75))
            ch1_notes.append(Note(1, 49, offset + 0.75, offset + 0.8125))
            ch1_notes.append(Note(1, 49, offset + 0.875, offset + 1.0))
            ch1_notes.append(Note(1, 49, offset + 1.125, offset + 1.25))
            ch1_notes.append(Note(1, 49, offset + 1.25, offset + 1.3125))
            ch1_notes.append(Note(1, 49, offset + 1.5, offset + 1.75))
            ch1_notes.append(Note(1, 49, offset + 1.75, offset + 1.8125))
            ch1_notes.append(Note(1, 49, offset + 1.875, offset + 1.9375))

        # 2. Random Melody Base
        for i in range(int(s * 2)):
            delay = 0.0
            if random.random() < 0.4: delay = int(random.random() * 3) * 0.5
            if random.random() < 0.2: delay = int(random.random() * 3) * 0.25

            if random.random() > 0.25:
                r_val = int(random.random()**2 * 3) * 2 - 2
                vv_sub = vv if random.random() < 0.2 else 0
                key = 49 - 12 + int(random.random() * 3) * 12 - 12 + v + 0 * r_val - vv_sub
                
                note_start = base_beat + (i / s) + (delay / s)
                note_end = base_beat + (i / s) + (1.0 / s) + (delay / s)
                ch0_notes.append(Note(0, key, note_start, note_end))

        # 3. Echo/Copy the melody with offsets
        new_notes = []
        for note in ch0_notes:
            new_notes.append(Note(0, note.key + v1, note.start + 2.0, note.end + 2.0))
            new_notes.append(Note(0, note.key + v2, note.start + 4.0, note.end + 4.0))
            new_notes.append(Note(0, note.key + v3, note.start + 6.0, note.end + 6.0))
        ch0_notes.extend(new_notes)

        # 4. Bass track notes
        ch0_notes.append(Note(0, 49 + v, base_beat, base_beat + 2.0, 0.5))
        ch0_notes.append(Note(0, 49 + v + v1, base_beat + 2.0, base_beat + 4.0, 0.5))
        ch0_notes.append(Note(0, 49 + v + v2, base_beat + 4.0, base_beat + 6.0, 0.5))
        ch0_notes.append(Note(0, 49 + v + v3, base_beat + 6.0, base_beat + 8.0, 0.5))

        # 5. SinWave Sweeps
        for note in list(ch0_notes):
            rel_start = note.start - base_beat
            if rel_start < 2.0: p = 49 + v
            elif rel_start < 4.0: p = 49 + v + v1
            elif rel_start < 6.0: p = 49 + v + v2
            elif rel_start < 8.0: p = 49 + v + v3
            else: p = 49 + v

            if random.random() > 0.5:
                p -= vv
                if random.random() > 0.5: p -= 3
            p -= 12

            if random.random() > 0.5:
                ch2_notes.append(Note(2, p, note.start, note.end, note.vol / 2.0))

        # 6. Duplicate everything into the 2nd half of the block (bars 3 & 4)
        ch0_dup, ch1_dup, ch2_dup = [], [], []
        for n in ch0_notes:
            ch0_dup.append(Note(0, n.key, n.start + 8.0, n.end + 8.0, n.vol))
            ch0_dup.append(Note(0, n.key + 12, n.start + 8.0, n.end + 8.0 + 0.375, n.vol / 2.0))
        for n in ch1_notes:
            ch1_dup.append(Note(1, n.key, n.start + 8.0, n.end + 8.0, n.vol))
        for n in ch2_notes:
            ch2_dup.append(Note(2, n.key, n.start + 8.0, n.end + 8.0, n.vol))

        ch0_notes.extend(ch0_dup)
        ch1_notes.extend(ch1_dup)
        ch2_notes.extend(ch2_dup)

        # 7. Add extra hi-hat and beat to the 2nd half
        for i in [8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5, 15.0, 15.5]:
            ch1_notes.append(Note(1, 49 - 24, base_beat + i + 0.25, base_beat + i + 0.375, 2.0))
            ch2_notes.append(Note(2, 65, base_beat + i, base_beat + i + 0.125, 6.0))

        # 8. Cymbal crash at the start of the 2nd half
        ch1_notes.append(Note(1, 49 - 12, base_beat + 8.0, base_beat + 10.0, 0.5))

        song.channels[0].notes.extend(ch0_notes)
        song.channels[1].notes.extend(ch1_notes)
        song.channels[2].notes.extend(ch2_notes)

    return song

# -----------------------------------------------------------------------------
# Audio Render and Export
# -----------------------------------------------------------------------------

def render_channel_audio(channel, total_samples, samples_per_beat, sample_rate, fix_pitch):
    """
    Worker function to render a single channel's audio completely independent of others.
    """
    channel_data = [0.0] * total_samples
    for note in channel.notes:
        start_sample = int(note.start * samples_per_beat)
        end_sample = int(note.end * samples_per_beat)
        
        # Prevent out-of-bounds writing
        start_sample = max(0, start_sample)
        end_sample = min(total_samples, end_sample)

        for t in range(start_sample, end_sample):
            val = channel.instrument.generator(t, note.key, start_sample, end_sample, sample_rate, fix_pitch)
            channel_data[t] += val * note.vol
            
    return channel_data

def generate_audio(song, sample_rate, bpm, fix_pitch, use_threads):
    """
    Renders the discrete Note objects into a raw audio sample array.
    """
    samples_per_beat = int(sample_rate * 60.0 / bpm)
    total_samples = int(song.bars * song.beats_per_bar * samples_per_beat)
    audio_data = [0.0] * total_samples

    total_notes = sum(len(c.notes) for c in song.channels)
    
    if use_threads:
        print(f"Synthesizing {total_notes} notes across {len(song.channels)} channels (Parallel Generation Enabled)...")
        # ProcessPoolExecutor yields true multi-core parallel processing in Python
        with concurrent.futures.ProcessPoolExecutor(max_workers=len(song.channels)) as executor:
            futures = [
                executor.submit(
                    render_channel_audio, 
                    channel, total_samples, samples_per_beat, sample_rate, fix_pitch
                ) for channel in song.channels
            ]
            
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                ch_data = future.result()
                # Merge the parallelly generated channel into the master track
                for t in range(total_samples):
                    audio_data[t] += ch_data[t]
                
                completed += 1
                sys.stdout.write(f'\rRendered channel {completed}/{len(song.channels)}')
                sys.stdout.flush()
    else:
        # Sequential Generation
        processed_notes = 0
        for channel in song.channels:
            for note in channel.notes:
                start_sample = int(note.start * samples_per_beat)
                end_sample = int(note.end * samples_per_beat)
                start_sample = max(0, start_sample)
                end_sample = min(total_samples, end_sample)

                for t in range(start_sample, end_sample):
                    val = channel.instrument.generator(t, note.key, start_sample, end_sample, sample_rate, fix_pitch)
                    audio_data[t] += val * note.vol
                
                processed_notes += 1
                sys.stdout.write(f'\rRendering audio... [{processed_notes}/{total_notes} notes synthesized]')
                sys.stdout.flush()
            
    print("\nApplying master volume limits...")

    channels_count = len(song.channels)
    scale_factor = 32767.0 / 4.0 / channels_count

    processed_audio = []
    for val in audio_data:
        scaled = val * scale_factor
        # 16-bit PCM integer boundaries
        clipped = max(-32768, min(int(round(scaled)), 32767))
        processed_audio.append(clipped)

    return processed_audio

def save_wav(filename, audio_data, sample_rate):
    """
    Saves the rendered audio data list to a WAV file.
    """
    print(f"Writing 16-bit PCM WAV to {filename}...")
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)      # Mono
        f.setsampwidth(2)      # 16-bit (2 bytes)
        f.setframerate(sample_rate)
        
        # Pack data rapidly using struct and bytearray
        packed = bytearray(len(audio_data) * 2)
        struct.pack_into(f'<{len(audio_data)}h', packed, 0, *audio_data)
        f.writeframes(packed)
    print("Done! Enjoy the music.")

# -----------------------------------------------------------------------------
# CLI Entry Point
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Algorithmic Song Generator")
    parser.add_argument('--length', type=int, default=4, help='Length of the song in bars (multiple of 4 works best).')
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducible songs.')
    parser.add_argument('--bpm', type=float, default=70.0, help='Tempo in BPM (default 70 aligns with original timing).')
    parser.add_argument('--sample-rate', type=int, default=44100, help='Output sample rate (Hz).')
    parser.add_argument('--output', type=str, default='output.wav', help='Output base filename.')
    parser.add_argument('--fix-pitch', action='store_true', help='Fix the quirky JS pitch calculations to use true chromatic frequencies.')
    parser.add_argument('--multithread', action='store_true', help='Enable parallel processing for much faster generation.')

    args = parser.parse_args()

    # Determine seed dynamically if none was provided
    actual_seed = args.seed if args.seed is not None else random.randint(10000, 99999)

    # Automatically construct the filename with the seed embedded
    base_name, ext = os.path.splitext(args.output)
    final_output = f"{base_name}_{actual_seed}{ext}"

    print(f"--- Algorithm Music Generator ---")
    print(f"Length:    {args.length} bars")
    print(f"Tempo:     {args.bpm} BPM")
    print(f"Seed:      {actual_seed}")
    print(f"Output to: {final_output}")

    # 1. Generate Song layout
    my_song = compose_song(args.length, actual_seed)
    
    # 2. Render to float audio track
    audio_track = generate_audio(my_song, args.sample_rate, args.bpm, args.fix_pitch, args.multithread)
    
    # 3. Export WAV
    save_wav(final_output, audio_track, args.sample_rate)