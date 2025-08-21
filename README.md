# DatPlot Overview

[summary]

# Documentation

Full documentation can be found on [GitHub pages](https://osudsl.github.io/datplots/).

# Download

The Datplot download can be found under [releases](https://github.com/OSUDSL/datplots/releases)

## Running the Program Locally

Clone the repository to a local device and run these commands to get datplot running locally

    uv sync
    uv run datplot
    
## Getting an updated executable

    uv run -m PyInstaller --windowed --icon=toy.ico --onefile --hidden-import numpy --collect-all nicegui src/datPlot.py
    
