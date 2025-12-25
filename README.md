# USD Frame Tools

Merge USD frame sequences into a single time-sampled USD file. Optimized for Storm Hydro/VFX, Houdini or others simulations tools with memory-efficient processing.

## Features

- ✅ Merge USD frame sequences (1 file per frame) into single USDC
- ✅ Memory optimized (configurable save intervals)
- ✅ Preserve custom attributes (emitterId, velocities, etc.)
- ✅ No interpolation on integer attributes
- ✅ USD tree inspection (like usdtree)
- ✅ Cross-platform (Windows/Linux/macOS)

## Installation

### Windows (WSL2 - Recommended)
```bash
# Install WSL2 via Windows tools (recommended for beginers)
Tutorial: "https://www.youtube.com/watch?v=OvxLXx49cfk"

# Install WSL2 command line (if not already installed)
wsl --install

# Inside WSL, run:
sudo apt update
sudo apt install -y python3-pip
pip3 install usd-core

# Download the script
cd $HOME
mkdir USDFrameToUSDC
cd USDFrameToUSDC
wget https://raw.githubusercontent.com/MattRM2/USD-Frame-To-USDC/refs/heads/main/USDFrameToUSDC.py
chmod +x USDFrameToUSDC.py

# Init the path in .bashrc
nano $HOME/.bashrc

After the last line, add: export USD=$HOME/USDFrameToUSDC/
Do the shortcut ctrl+o (and enter to write the file) and ctrl+x and source the new .bashrc

source ~/.bashrc
```
Test installation: 
```bash
cd /
python3 $USD/USDFrameToUSDC.py -h
```
Help is displayed in the terminal, and the installation is complete.

### Linux / macOS
```bash
pip3 install usd-core
wget https://raw.githubusercontent.com/MattRM2/USD-Frame-To-USDC/refs/heads/main/USDFrameToUSDC.py
chmod +x USDFrameToUSDC.py
```
You can have the path like on WSL to your system too.

## Usage

### Merge USD Sequence
```bash
# Basic merge
python3 $USD/USDFrameToUSDC.py -i ./sim/frame.{frame:04d}.usd -o merged.usdc -s 0 -e 200

# With custom prim path
python3 $USD/USDFrameToUSDC.py -i ./FlipSystem.fluid.{frame:04d}.usd -o output.usdc -s 1 -e 250 -p /Root/Points

# Memory optimization (save every 5 frames)
python3 $USD/USDFrameToUSDC.py -i ./sim/frame.{frame:04d}.usd -o merged.usdc -s 0 -e 500 --save-interval 5
```

### Inspect USD File
```bash
# Display hierarchy
python3 $USD/USDFrameToUSDC.py -t ./frame.0001.usd

# Limit depth
python3 $USD/USDFrameToUSDC.py -t ./frame.0001.usd --max-depth 3
```

### Navigate to your Windows drive
All Windows drives are located under /mnt in WSL
```bash
cd /mnt
ls
```
You can use "cd" to navigate to the folder containing your USD frames.

### Configure your WSL virtual machine
Open the Windows menu and search for WSL settings and open it. Now you can change parameters to have the ressources needed. Always keep 30% of ram for Windows (e.g. 128gb of ram, give 90Gb to the virtual machine max).


## Command Line Options
```
-i, --input         Input USD file pattern (e.g., "./sim/frame_{frame:04d}.usd")
-o, --output        Output USD file path (e.g., "merged.usdc")
-s, --start         Start frame number
-e, --end           End frame number
-p, --prim-path     Prim path in USD file (default: /)
--save-interval     Save every N frames to optimize memory (default: 10)
-t, --tree          Display USD file hierarchy
--max-depth         Maximum depth for tree display
-h, --help          Show help message
```

## Memory Optimization

For large simulations (>1M points), adjust `--save-interval`:

- **64GB+ RAM**: `--save-interval 20` (faster)
- **32GB RAM**: `--save-interval 10` (balanced)
- **16GB RAM**: `--save-interval 5` (more conservative)

## Examples

### Storm Hydro Workflow
```bash
# 1. Export from Storm Hydro (1 USD per frame)
# 2. Merge into single file
python3 $USD/USDFrameToUSDC.py -i ./FlipSystem.fluid.{frame:04d}.usd -o simulation.usdc -s 0 -e 200 -p /Root/Points

# 3. Import in Blender (File > Import > USD) with scale option to 10
```

### Inspect Before Merging
```bash
# Check the structure of your first frame
python3 $USD/USDFrameToUSDC.py -t ./FlipSystem.fluid.0001.usd

# Find the correct prim path, then merge
python3 $USD/USDFrameToUSDC.py -i ./FlipSystem.fluid.{frame:04d}.usd -o output.usdc -s 0 -e 200 -p /YOUR/PRIM/PATH
```

### Import in Blender 5.0.x
[![Watch the video](https://img.youtube.com/vi/94skWnEihzI/0.jpg)](https://www.youtube.com/watch?v=94skWnEihzI)

## Troubleshooting

**"Frame X manquante"**: Some frames are missing in the sequence (script continues with available frames)

**"Prim not found"**: Check the prim path with `-t` option first

**Out of memory**: Reduce `--save-interval` value (e.g., `--save-interval 5`)

## Tested With

- Storm Hydro 1.x+ fluid simulations / Storm VFX
- Houdini USD exports
- Maya USD exports
- Blender 4.x/5.x USD import

## Requirements

- Python 3.8+
- USD (Pixar) - `pip install usd-core`

## License

MIT License - Free to use for personal and commercial projects

## Contributing

Issues and PRs welcome!

## Author

Created for Storm Hydro/VFX, Houdini or others pipeline workflows by Matthieu "MattRM" Barbié & Claude Ai.
