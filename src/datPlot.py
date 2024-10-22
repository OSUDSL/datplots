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
        self.graph_dropdown = None # first dropdown for y-axis
        self.second_graph_dropdown = None  # second dropdown for y-axis
        self.x_axis_dropdown = None #dropdown for x axis
        self.dat_file_data = None  # store dat file data
        self.plot_container = None  # container for the plot

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
                ["Select Graph"],
                value="Select Graph",
                label="Select Y-axis 1",
                on_change=self.plot_selected_column,  # column selection
            )

            # Dropdown for second Y-axis (column) selection
            self.second_graph_dropdown = ui.select(
                ["Select Graph"],
                value="Select Graph",
                label="Select Y-axis 2 (optional)",
                on_change=self.plot_selected_column,  # column selection
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
            self.second_graph_dropdown.options = columns  # Update second dropdown as well
            self.graph_dropdown.update()  # Refresh and display the new options
            self.second_graph_dropdown.update()

        except Exception as ex:
            logger.error(f"Error reading .dat file: {ex}")
            ui.notify("Error reading .dat file")

    def plot_selected_column(self):
        """Plot the selected columns from the .dat file."""

        y_column_1 = self.graph_dropdown.value  # First y-axis column
        y_column_2 = self.second_graph_dropdown.value  # Second y-axis column
        x_column = self.x_axis_dropdown.value  # x axis

        if self.dat_file_data is not None and y_column_1 in self.dat_file_data.columns:
            # Get data for the first y-axis
            x_data = self.dat_file_data[x_column].to_numpy()
            y_data_1 = self.dat_file_data[y_column_1].to_numpy()

            # Create the first trace for the left y-axis
            fig = go.Figure(data=go.Scatter(x=x_data, y=y_data_1, name=y_column_1, yaxis='y1'))

            # If a second Y-axis column is selected, add it as a second trace
            if y_column_2 != "Select Graph" and y_column_2 in self.dat_file_data.columns:
                y_data_2 = self.dat_file_data[y_column_2].to_numpy()
                fig.add_trace(go.Scatter(x=x_data, y=y_data_2, name=y_column_2, yaxis='y2'))

            # Update layout to add a second Y-axis on the right side
            fig.update_layout(
                title=f"Plot of {y_column_1} and {y_column_2} vs {x_column}",
                autosize=True,  # Allow plot to auto-resize
                height=None,  # Let height be determined by the container
                yaxis=dict(
                    title=y_column_1,
                    side="left"
                ),
                yaxis2=dict(
                    title=y_column_2,
                    side="right",
                    overlaying="y",  # Overlay on the same x-axis
                    position=1  # Position the second Y-axis on the right
                )
            )

            # Clear the container before adding the new plot
            self.plot_container.clear()  # Remove previous plot

            # Add the new plot
            with self.plot_container:
                ui.plotly(fig).style('width: 100%; height: 100%;')  # Make plot responsive


def init_gui():
    page = MainDataPage()
    page.page_creation()

    # Start the NiceGUI app
    ui.run(native=True)


if __name__ in {"__main__", "__mp_main__"}:
    init_gui()

