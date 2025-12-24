# USD Frame Tools

Merge USD frame sequences into a single time-sampled USD file. Optimized for Storm Hydro/VFX, Houdini or others simulations with memory-efficient processing.

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
# Install WSL2 (if not already installed)
wsl --install

# Inside WSL, run:
sudo apt update
sudo apt install -y python3-pip
pip3 install usd-core --break-system-packages

# Download the script
cd ~
wget https://github.com/YOUR_USERNAME/usd-frame-tools/raw/main/USDFrameToUSDC.py
chmod +x USDFrameToUSDC.py
```

### Linux / macOS
```bash
pip3 install usd-core
wget https://github.com/YOUR_USERNAME/usd-frame-tools/raw/main/USDFrameToUSDC.py
chmod +x USDFrameToUSDC.py
```
You can add the directory containing the script to your WSL Linux PATH environment variable, so you can call it from anywhere

## Usage

### Merge USD Sequence
```bash
# Basic merge
python3 USDFrameToUSDC.py -i "./sim/frame_{frame:04d}.usd" -o merged.usdc -s 0 -e 200

# With custom prim path
python3 USDFrameToUSDC.py -i "./FlipSystem.fluid.{frame:04d}.usd" -o output.usdc -s 1 -e 250 -p /Root/Points

# Memory optimization (save every 5 frames)
python3 USDFrameToUSDC.py -i "./sim/frame_{frame:04d}.usd" -o merged.usdc -s 0 -e 500 --save-interval 5
```

### Inspect USD File
```bash
# Display hierarchy
python3 USDFrameToUSDC.py -t frame_0001.usd

# Limit depth
python3 USDFrameToUSDC.py -t frame_0001.usd --max-depth 3
```

### From Windows PowerShell (using WSL)
```powershell
# Navigate to your simulation folder
cd G:\YOUR_SIMULATIONS

# Run via WSL
wsl python3 USDFrameToUSDC.py -i "./FlipSystem.fluid.{frame:04d}.usd" -o merged.usdc -s 0 -e 200
```

## Command Line Options
```
-i, --input         Input USD file pattern (e.g., "./sim/frame_{frame:04d}.usd")
-o, --output        Output USD file path (e.g., "merged.usdc")
-s, --start         Start frame number
-e, --end           End frame number
-p, --prim-path     Prim path in USD file (default: /Root/Points)
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
python3 USDFrameToUSDC.py -i "./FlipSystem.fluid.{frame:04d}.usd" -o simulation.usdc -s 0 -e 200 -p /Root/Points

# 3. Import in Blender (File > Import > USD)
```

### Inspect Before Merging
```bash
# Check the structure of your first frame
python3 USDFrameToUSDC.py -t FlipSystem.fluid.0001.usd

# Find the correct prim path, then merge
python3 USDFrameToUSDC.py -i "./FlipSystem.fluid.{frame:04d}.usd" -o output.usdc -s 0 -e 200 -p /YOUR/PRIM/PATH
```

## Troubleshooting

**"Frame X manquante"**: Some frames are missing in the sequence (script continues with available frames)

**"Prim not found"**: Check the prim path with `-t` option first

**Out of memory**: Reduce `--save-interval` value (e.g., `--save-interval 5`)

## Tested With

- Storm Hydro 1.x+ fluid simulations
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

Created for Storm Hydro/VFX, Houdini or others pipeline workflows by Matthieu "MattRM" Barbié & Claude Ai."# USD-Frame-To-USDC" 
