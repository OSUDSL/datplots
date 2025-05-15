import os
import polars as pl
from loguru import logger
from src._plotGraphs import plot_selected_column

def pick_dat_file(self):
        logger.info(f"DAT file {self.dat_filename} selected")

        # Clear previous plots and histograms
        if self.plot_container:
            self.plot_container.clear()
        if self.histogram_container:
            self.histogram_container.clear()

        # Reset dropdowns
        self.graph_dropdown.value = "Select Graph"
        self.second_graph_dropdown.value = "Select Graph"
        self.graph_dropdown.options = []
        self.second_graph_dropdown.options = []
        self.graph_dropdown.update()
        self.second_graph_dropdown.update()

        # Update the filename label
        self.current_filename_label.text = f"Current File: {os.path.basename(self.dat_filename)}"
        self.current_filename_label.update()

        # Load the dat file using polars
        self.dat_file_data = pl.read_csv(self.dat_filename, separator=" ", has_header=True)

        # Filter columns to include only ints and floats
        columns = [
            col for col, dtype in self.dat_file_data.schema.items()
            if dtype in [pl.Float64, pl.Int64, pl.Float32, pl.Int32]
        ]

        logger.info(f"Columns loaded: {columns}")

        # Update dropdown options
        self.graph_dropdown.options = columns
        self.second_graph_dropdown.options = columns
        self.graph_dropdown.update()
        self.second_graph_dropdown.update()

        # Set the initial min and max range based on the x-axis data
        x_column = self.x_axis_dropdown.value
        x_data = self.dat_file_data[x_column].to_numpy()
        x_beginning = x_data.min()
        x_end = x_data.max()

        # Store the original range for resetting
        self.original_min_max = {'min': x_beginning, 'max': x_end}

        # Auto-plot the first column or default to instructions
        if len(columns) > 0:
            self.graph_dropdown.value = columns[0]
            self.graph_dropdown.update()
            plot_selected_column(self)  # Automatically plot the first column`