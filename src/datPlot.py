from nicegui import ui, app
from nicegui.events import UploadEventArguments
import os
import polars as pl
import numpy as np
import plotly.graph_objects as go
from loguru import logger


class MainDataPage:
    def __init__(self) -> None:
        """The page is created as soon as the class is instantiated."""
        self.main_layout = None
        self.graph_dropdown = None
        self.x_axis_dropdown = None
        self.dat_file_data = None  # Store the dat file data
        self.plot_container = None  # Container for the plot

    def page_creation(self):
        # Create the main UI elements
        with ui.row(align_items="center").style("width:100%"):
            ui.label("Dat File Plot").classes("text-2xl font-bold mb-2")
            ui.space()

            # Dropdown for x-axis selection (SimTime / DatTime)
            self.x_axis_dropdown = ui.select(
                ["SimTime", "DatTime"],
                value="SimTime",  # Defaults to SimTime
                label="Select X-axis"
            )

            # Dropdown for y-axis (column) selection
            self.graph_dropdown = ui.select(
                ["Select Graph"],  #empty, will be populated after file upload
                value="Select Graph",
                label="Select Y-axis",
                on_change=self.plot_selected_column,  #column selection
            )
            ui.upload(
                on_upload=self.handle_dat_file,
            )

        # Create a container for the plot
        self.plot_container = ui.element('div').style('width: 100%; height: 100vh;')  # Full width, dynamic height

    def handle_dat_file(self, e: UploadEventArguments):
        """Handle the .dat file upload."""
        if not e.name.endswith('.dat'):
            ui.notify("Please upload a valid .dat file")
            return

        dat_file_path = os.path.join("/tmp", e.name)  # Save the file to /tmp
        try:
            # Read from the temp file and write to a new file
            with open(dat_file_path, 'wb') as f:
                f.write(e.content.read())  # Read the content and write as bytes
            logger.info(f"Uploaded .dat file: {dat_file_path}")

            # Load the dat file using polars
            self.dat_file_data = pl.read_csv(dat_file_path, separator=" ", has_header=True)  # First line headers
            columns = [col for col in self.dat_file_data.columns if col]  # Filter out any empty column names
            logger.info(columns)

            # Update the dropdown options
            self.graph_dropdown.options = columns
            self.graph_dropdown.update()  # Refresh and display the new options

        except Exception as ex:
            logger.error(f"Error reading .dat file: {ex}")
            ui.notify("Error reading .dat file")

    def plot_selected_column(self):
        """Plot the selected column from the .dat file."""

        y_column = self.graph_dropdown.value #y axis
        x_column = self.x_axis_dropdown.value  # x axis

        if self.dat_file_data is not None and y_column in self.dat_file_data.columns:
            # Get data for x and y axes
            x_data = self.dat_file_data[x_column].to_numpy()
            y_data = self.dat_file_data[y_column].to_numpy()
            # Create a Plotly figure
            fig = go.Figure(data=go.Scatter(x=x_data, y=y_data))
            fig.update_layout(
                title=f"Plot of {y_column} vs {x_column}",
                autosize=True,  # Allow plot to auto-resize
                height=None  # Let  height be determined by the container
            )

            # Clear the container before adding the new plot
            self.plot_container.clear()  # Remove previous plot

            # Clear the container and then add the new plot
            with self.plot_container:
                ui.plotly(fig).style('width: 100%; height: 100%;')  # Make plot responsive

    #


def init_gui():
    page = MainDataPage()
    page.page_creation()

    # Start the NiceGUI app
    ui.run(native=True)


if __name__ in {"__main__", "__mp_main__"}:
    init_gui()
