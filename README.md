# DatPlot Overview

DatPlot is a program that helps users view and analyze data. By uploading your data files, you can generate interactive line graphs and histograms. The program also allows you to adjust axis points, making it easy to focus on different variables in the dataset

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

# Credits

Pydre was developed by The Ohio State University [Driving Simulation Lab](https://drivesim.osu.edu/).
