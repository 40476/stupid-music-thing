```
usage: main.py [-h] [--length LENGTH] [--seed SEED] [--bpm BPM] [--sample-rate SAMPLE_RATE] [--output OUTPUT] [--fix-pitch] [--multithread] [--style {retro,ambient,techno,orchestral,experimental,classic}]

Algorithmic Song Generator

options:
  -h, --help            show this help message and exit
  --length LENGTH       Length of the song in bars (multiple of 4 works best).
  --seed SEED           Random seed for reproducible songs.
  --bpm BPM             Tempo in BPM (default 70 aligns with original timing).
  --sample-rate SAMPLE_RATE
                        Output sample rate (Hz).
  --output OUTPUT       Output base filename.
  --fix-pitch           Fix the quirky JS pitch calculations to use true chromatic frequencies.
  --multithread         Enable parallel processing for much faster generation.
  --style {retro,ambient,techno,orchestral,experimental,classic}
                        Music style preset (classic, retro, ambient, techno, orchestral, experimental).
```
