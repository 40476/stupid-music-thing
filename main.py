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
import multiprocessing
from collections import defaultdict

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
    The "Piano" instrument (soft, plucky sound with a sawtooth envelope based on pitch).
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
    The "SinWave" instrument (soft sine wave, good for melodies and pads).
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
    The "Noise" instrument (percussive, random noise with a sawtooth envelope based on pitch).
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

def square_gen(t, key, s, e, sample_rate, fix_pitch):
    """
    The "Square" instrument (8-bit style square wave, like retro game music).
    """
    if fix_pitch:
        freq = get_freq(key)
    else:
        freq = get_freq(88.0 - key - 3.75)
    
    if freq <= 0: return 0
    
    vol = max(0.0, 1.0 - (t - s) / (e - s)) ** 0.5
    
    if fix_pitch:
        phase = 2.0 * math.pi * t * freq / sample_rate
    else:
        phase = (((t * freq) % sample_rate) / sample_rate) * math.pi * 2.0
    
    # Square wave: only positive or negative
    square_val = 1.0 if math.sin(phase) >= 0 else -1.0
    return square_val * vol

def triangle_gen(t, key, s, e, sample_rate, fix_pitch):
    """
    The "Triangle" instrument (softer than square, with a more mellow tone).
    """
    if fix_pitch:
        freq = get_freq(key)
    else:
        freq = get_freq(88.0 - key - 3.75)
    
    if freq <= 0: return 0
    
    vol = max(0.0, 1.0 - (t - s) / (e - s)) ** 0.75
    
    if fix_pitch:
        phase = 2.0 * math.pi * t * freq / sample_rate
    else:
        phase = (((t * freq) % sample_rate) / sample_rate) * math.pi * 2.0
    
    # Triangle wave using arcsin of sin
    triangle_val = (2.0 / math.pi) * math.asin(math.sin(phase))
    return triangle_val * vol

def organ_gen(t, key, s, e, sample_rate, fix_pitch):
    """
    The "Organ" instrument (adds harmonics for a richer, sustained sound).
    """
    if fix_pitch:
        freq = get_freq(key)
    else:
        freq = get_freq(88.0 - key - 3.75)
    
    if freq <= 0: return 0
    
    # Organ has slow attack and long sustain
    progress = (t - s) / (e - s) if e > s else 0
    attack = min(1.0, progress * 10.0)  # Quick attack
    release = max(0.0, 1.0 - max(0.0, progress - 0.7) / 0.3)  # Late release
    vol = min(attack, release) ** 0.5
    
    # Add harmonics (octave + fifth + octave)
    result = 0.0
    result += math.sin(2.0 * math.pi * t * freq / sample_rate) * 0.5
    result += math.sin(2.0 * math.pi * t * freq * 1.5 / sample_rate) * 0.25
    result += math.sin(2.0 * math.pi * t * freq * 2.0 / sample_rate) * 0.15
    result += math.sin(2.0 * math.pi * t * freq * 3.0 / sample_rate) * 0.1
    
    return result * vol

def bass_gen(t, key, s, e, sample_rate, fix_pitch):
    """
    The "Bass" instrument (deep, punchy sound with a sawtooth base and some harmonics).
    """
    if fix_pitch:
        freq = get_freq(key)
    else:
        freq = get_freq(88.0 - key - 3.75)
    
    if freq <= 0: return 0
    
    # Punchy envelope - quick attack, medium decay
    progress = (t - s) / (e - s) if e > s else 0
    vol = max(0.0, 1.0 - progress) ** 1.5
    
    # Sawtooth-like bass with some harmonics
    period = sample_rate / freq
    if period <= 0: return 0
    
    saw_val = 2.0 * ((t % period) / period - 0.5)
    result = saw_val * 0.7
    result += math.sin(2.0 * math.pi * t * freq * 2.0 / sample_rate) * 0.2
    result += math.sin(2.0 * math.pi * t * freq * 3.0 / sample_rate) * 0.1
    
    return result * vol

def pad_gen(t, key, s, e, sample_rate, fix_pitch):
    """
    The "Pad" instrument (soft, sustained sound with multiple detuned oscillators for a rich texture).
    """
    if fix_pitch:
        freq = get_freq(key)
    else:
        freq = get_freq(88.0 - key - 3.75)
    
    if freq <= 0: return 0
    
    # Very slow attack and release for pad sound
    progress = (t - s) / (e - s) if e > s else 0
    attack = min(1.0, progress * 3.0)  # Slow attack
    release = max(0.0, 1.0 - max(0.0, progress - 0.5) / 0.5)
    vol = min(attack, release) * 0.3  # Quieter for background
    
    # Detuned dual oscillators for rich pad sound
    result = 0.0
    result += math.sin(2.0 * math.pi * t * freq / sample_rate) * 0.5
    result += math.sin(2.0 * math.pi * t * freq * 1.005 / sample_rate) * 0.3  # Slightly detuned
    result += math.sin(2.0 * math.pi * t * freq * 2.0 / sample_rate) * 0.15
    
    return result * vol

def arp_gen(t, key, s, e, sample_rate, fix_pitch):
    """
    The "Arp" instrument (plucky, percussive sound for arpeggios).
    """
    if fix_pitch:
        freq = get_freq(key)
    else:
        freq = get_freq(88.0 - key - 3.75)
    
    if freq <= 0: return 0
    
    # Very punchy - quick attack, fast decay
    progress = (t - s) / (e - s) if e > s else 0
    vol = max(0.0, 1.0 - progress * 3.0) ** 2.0
    
    period = sample_rate / freq
    if period <= 0: return 0
    
    # Bright, metallic sound
    saw_val = 2.0 * ((t % period) / period - 0.5)
    result = saw_val * 0.6
    result += math.sin(2.0 * math.pi * t * freq * 3.0 / sample_rate) * 0.2
    result += math.sin(2.0 * math.pi * t * freq * 4.0 / sample_rate) * 0.1
    
    return result * vol

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
# Style Presets
# -----------------------------------------------------------------------------

STYLE_PRESETS = {
    'retro': {
        'instruments': ['Square', 'Triangle', 'Noise'],
        'bpm_range': (100, 140),
        'melody_complexity': 0.8,
        'drum_intensity': 0.9
    },
    'ambient': {
        'instruments': ['Pad', 'SinWave', 'Organ'],
        'bpm_range': (60, 80),
        'melody_complexity': 0.3,
        'drum_intensity': 0.2
    },
    'techno': {
        'instruments': ['Square', 'Bass', 'Noise'],
        'bpm_range': (120, 160),
        'melody_complexity': 0.9,
        'drum_intensity': 1.0
    },
    'orchestral': {
        'instruments': ['SinWave', 'Organ', 'Pad'],
        'bpm_range': (70, 100),
        'melody_complexity': 0.6,
        'drum_intensity': 0.4
    },
    'experimental': {
        'instruments': ['Arp', 'Bass', 'Noise', 'Pad'],
        'bpm_range': (80, 120),
        'melody_complexity': 1.0,
        'drum_intensity': 0.7
    },
    'classic': {
        'instruments': ['Piano', 'SinWave', 'Noise'],
        'bpm_range': (70, 90),
        'melody_complexity': 0.5,
        'drum_intensity': 0.5
    }
}

# -----------------------------------------------------------------------------
# Algorithmic Composition
# -----------------------------------------------------------------------------

def get_instrument_by_name(name):
    """Get instrument generator function by name."""
    instrument_map = {
        'Piano': piano_gen,
        'Noise': noise_gen,
        'SinWave': sinwave_gen,
        'Square': square_gen,
        'Triangle': triangle_gen,
        'Organ': organ_gen,
        'Bass': bass_gen,
        'Pad': pad_gen,
        'Arp': arp_gen
    }
    return instrument_map.get(name, piano_gen)

def compose_song(bars, seed, style='classic'):
    """
    Composes a song algorithmically based on the provided random seed and style.
    Replicates the random sequence from the original JavaScript.
    """
    if seed is not None:
        random.seed(seed)
        
    song = Song(bars)
    
    # Get style configuration
    style_config = STYLE_PRESETS.get(style, STYLE_PRESETS['classic'])
    instruments = style_config['instruments']
    melody_complexity = style_config['melody_complexity']
    drum_intensity = style_config['drum_intensity']
    
    # Setup Instruments based on style
    for i, inst_name in enumerate(instruments):
        instrument = Instrument(inst_name, get_instrument_by_name(inst_name))
        song.channels.append(Channel(i, instrument))
    
    # Add extra channels if needed (up to 5 total)
    while len(song.channels) < 5:
        fallback_inst = Instrument('Piano', piano_gen)
        song.channels.append(Channel(len(song.channels), fallback_inst))

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

        # Variation: different scale patterns based on block
        scale_offset = random.choice([0, 2, 4, 5, 7, 9, 11])  # Major scale intervals
        
        ch0_notes = []
        ch1_notes = []
        ch2_notes = []
        
        # Additional channels for more variation
        ch3_notes = []
        ch4_notes = []

        # 1. Generate Drum Beat (First 2 bars) with style-based intensity
        drum_count = int(10 * drum_intensity)
        for i in range(0, 8, 2):
            offset = base_beat + float(i)
            # Kick drum pattern
            ch1_notes.append(Note(1, 49, offset, offset + 0.125, drum_intensity))
            ch1_notes.append(Note(1, 49, offset + 0.25, offset + 0.3125, drum_intensity))
            ch1_notes.append(Note(1, 49, offset + 0.5, offset + 0.75, drum_intensity))
            ch1_notes.append(Note(1, 49, offset + 0.75, offset + 0.8125, drum_intensity))
            ch1_notes.append(Note(1, 49, offset + 0.875, offset + 1.0, drum_intensity))
            ch1_notes.append(Note(1, 49, offset + 1.125, offset + 1.25, drum_intensity))
            ch1_notes.append(Note(1, 49, offset + 1.25, offset + 1.3125, drum_intensity))
            ch1_notes.append(Note(1, 49, offset + 1.5, offset + 1.75, drum_intensity))
            ch1_notes.append(Note(1, 49, offset + 1.75, offset + 1.8125, drum_intensity))
            ch1_notes.append(Note(1, 49, offset + 1.875, offset + 1.9375, drum_intensity))
            
            # Hi-hat patterns (more active with higher intensity)
            if drum_intensity > 0.5:
                for hat_beat in [0.125, 0.375, 0.625, 0.875, 1.125, 1.375, 1.625, 1.875]:
                    ch1_notes.append(Note(1, 49 - 24, offset + hat_beat, offset + hat_beat + 0.0625, drum_intensity * 0.5))

        # 2. Random Melody Base with style-based complexity
        melody_count = int(s * 2 * melody_complexity)
        for i in range(melody_count):
            delay = 0.0
            if random.random() < 0.4: delay = int(random.random() * 3) * 0.5
            if random.random() < 0.2: delay = int(random.random() * 3) * 0.25

            if random.random() > (1.0 - melody_complexity * 0.5):
                r_val = int(random.random()**2 * 3) * 2 - 2
                vv_sub = vv if random.random() < 0.2 else 0
                # Use scale-aware note selection for better musicality
                key = 49 - 12 + int(random.random() * 3) * 12 - 12 + v + scale_offset + r_val - vv_sub
                
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

        # 9. Additional variation: Arpeggio patterns for higher channels
        if len(song.channels) > 3:
            arp_patterns = [
                [0, 4, 7, 12],  # Major arpeggio
                [0, 3, 7, 12],  # Minor arpeggio
                [0, 4, 8, 12],  # Augmented arpeggio
                [0, 3, 6, 12]   # Diminished arpeggio
            ]
            pattern = random.choice(arp_patterns)
            root = 49 + v
            for beat_offset in [0, 2, 4, 6]:
                for interval in pattern:
                    note_time = base_beat + beat_offset + (pattern.index(interval) * 0.25)
                    if note_time < base_beat + 8:
                        ch3_notes.append(Note(3, root + interval, note_time, note_time + 0.2, 0.3))

        # 10. Pad/Atmosphere for extra channels
        if len(song.channels) > 4:
            pad_duration = 4.0
            for beat_offset in [0, 4, 8, 12]:
                pad_root = 49 + v - 12
                ch4_notes.append(Note(4, pad_root, base_beat + beat_offset, base_beat + beat_offset + pad_duration, 0.15))
                ch4_notes.append(Note(4, pad_root + 7, base_beat + beat_offset, base_beat + beat_offset + pad_duration, 0.1))

        song.channels[0].notes.extend(ch0_notes)
        song.channels[1].notes.extend(ch1_notes)
        song.channels[2].notes.extend(ch2_notes)
        if len(song.channels) > 3:
            song.channels[3].notes.extend(ch3_notes)
        if len(song.channels) > 4:
            song.channels[4].notes.extend(ch4_notes)

    return song

# -----------------------------------------------------------------------------
# Audio Render and Export
# -----------------------------------------------------------------------------

def render_channel_audio(channel, total_samples, samples_per_beat, sample_rate, fix_pitch, progress_dict=None):
    """
    Worker function to render a single channel's audio completely independent of others.
    Updates progress_dict with current progress if provided.
    """
    channel_data = [0.0] * total_samples
    total_notes = len(channel.notes)
    
    for idx, note in enumerate(channel.notes):
        start_sample = int(note.start * samples_per_beat)
        end_sample = int(note.end * samples_per_beat)
        
        # Prevent out-of-bounds writing
        start_sample = max(0, start_sample)
        end_sample = min(total_samples, end_sample)

        for t in range(start_sample, end_sample):
            val = channel.instrument.generator(t, note.key, start_sample, end_sample, sample_rate, fix_pitch)
            channel_data[t] += val * note.vol
        
        # Update progress in shared dict
        if progress_dict is not None:
            progress_dict[channel.id] = (channel.instrument.name, idx + 1, total_notes)
            
    return (channel.id, channel.instrument.name, channel_data)

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
        
        # Create a Manager dict for real-time progress tracking
        manager = multiprocessing.Manager()
        progress_dict = manager.dict()
        
        # Track channel info
        channel_info = {}
        for channel in song.channels:
            channel_info[channel.id] = {
                'name': channel.instrument.name,
                'total': len(channel.notes),
                'complete': False
            }
        
        # Print initial progress bars
        for ch_id in sorted(channel_info.keys()):
            info = channel_info[ch_id]
            print(f"  [{info['name']:>10}] |{'░' * 20}|     0/{info['total']} (  0.0%)")
        
        # Use ProcessPoolExecutor with progress monitoring
        with concurrent.futures.ProcessPoolExecutor(max_workers=len(song.channels)) as executor:
            futures = {
                executor.submit(render_channel_audio, channel, total_samples, samples_per_beat, sample_rate, fix_pitch, progress_dict): channel.id
                for channel in song.channels
            }
            
            completed = 0
            total_channels = len(futures)
            last_progress = {}
            
            while completed < total_channels:
                # Check for completed futures
                done, _ = concurrent.futures.wait(futures, timeout=0.05, return_when=concurrent.futures.FIRST_COMPLETED)
                
                for future in list(done):
                    if future.done():
                        ch_id = futures[future]
                        _, _, ch_data = future.result()
                        
                        # Merge the channel data into master track
                        for t in range(total_samples):
                            audio_data[t] += ch_data[t]
                        
                        # Mark channel as complete
                        channel_info[ch_id]['complete'] = True
                        completed += 1
                        futures.pop(future, None)
                
                # Build progress display
                progress_lines = []
                display_changed = False
                
                for ch_id in sorted(channel_info.keys()):
                    info = channel_info[ch_id]
                    if info['complete']:
                        bar = '█' * 20
                        line = f"  ✓ [{info['name']:>10}] |{bar}| {info['total']}/{info['total']} (100.0%)"
                    elif ch_id in progress_dict:
                        name, current, total = progress_dict[ch_id]
                        pct = (current / total * 100) if total > 0 else 0
                        bar_len = 20
                        filled = int(bar_len * current / total) if total > 0 else 0
                        bar = '█' * filled + '░' * (bar_len - filled)
                        line = f"    [{name:>10}] |{bar}| {current:>5}/{total} ({pct:5.1f}%)"
                        
                        # Check if progress changed
                        key = (ch_id, current)
                        if key != last_progress.get(ch_id):
                            display_changed = True
                            last_progress[ch_id] = key
                    else:
                        line = f"    [{info['name']:>10}] |{'░' * 20}|     0/{info['total']} (  0.0%)"
                    progress_lines.append(line)
                
                # Update display if progress changed
                if display_changed:
                    # Move cursor up and redraw
                    sys.stdout.write(f'\033[{len(progress_lines)}A')
                    for line in progress_lines:
                        # FIX: Write the line, clear to end of line (\033[K), and unconditionally add a newline
                        sys.stdout.write(f'\r\033[K{line}\n')
                    sys.stdout.flush()
            
            print()  # New line after all complete
    else:
        # Sequential Generation with per-channel progress
        print(f"Synthesizing {total_notes} notes across {len(song.channels)} channels (Sequential Generation)...")
        
        for channel in song.channels:
            ch_total = len(channel.notes)
            print(f"\n  Processing channel: {channel.instrument.name} ({ch_total} notes)")
            
            for note_idx, note in enumerate(channel.notes):
                start_sample = int(note.start * samples_per_beat)
                end_sample = int(note.end * samples_per_beat)
                start_sample = max(0, start_sample)
                end_sample = min(total_samples, end_sample)

                for t in range(start_sample, end_sample):
                    val = channel.instrument.generator(t, note.key, start_sample, end_sample, sample_rate, fix_pitch)
                    audio_data[t] += val * note.vol
                
                # Show per-note progress for this channel
                pct = (note_idx + 1) / ch_total * 100
                bar_len = 30
                filled = int(bar_len * (note_idx + 1) / ch_total)
                bar = '█' * filled + '░' * (bar_len - filled)
                sys.stdout.write(f'\r    Progress: |{bar}| {note_idx + 1}/{ch_total} ({pct:5.1f}%)')
                sys.stdout.flush()
            
            print()  # New line after channel complete
            
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
    parser.add_argument('--style', type=str, default='classic',
                        choices=list(STYLE_PRESETS.keys()),
                        help='Music style preset (classic, retro, ambient, techno, orchestral, experimental).')

    args = parser.parse_args()

    # Determine seed dynamically if none was provided
    actual_seed = args.seed if args.seed is not None else random.randint(10000, 99999)

    # Automatically construct the filename with the seed embedded
    base_name, ext = os.path.splitext(args.output)
    final_output = f"{base_name}_{actual_seed}{ext}"

    print(f"--- Algorithm Music Generator ---")
    print(f"Length:    {args.length} bars")
    print(f"Tempo:     {args.bpm} BPM")
    print(f"Style:     {args.style}")
    print(f"Seed:      {actual_seed}")
    print(f"Output to: {final_output}")

    # 1. Generate Song layout
    my_song = compose_song(args.length, actual_seed, style=args.style)
    
    # 2. Render to float audio track
    audio_track = generate_audio(my_song, args.sample_rate, args.bpm, args.fix_pitch, args.multithread)
    
    # 3. Export WAV
    save_wav(final_output, audio_track, args.sample_rate)