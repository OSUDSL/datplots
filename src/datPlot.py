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
        self.min_max_range = None #store min and max x values
        self.control_panel = None #control panel to change x axis
        self.reset = None #reset button for control panel
        self.original_min_max = None  # Store the original full range for resetting

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

            ui.button(
                "Load DAT file", on_click=self.pick_dat_file, icon="folder"
            )

        # Create a container for the plot
        self.plot_container = ui.element('div').style('width: 100%; height: 100vh;')  # Full width, dynamic height

        # Control Panel
        self.min_max_range = ui.range(min=0, max=100, value={'min': 20, 'max': 80})

        # Bind the change event to the plot_selected_column function
        self.min_max_range.on('change', self.plot_selected_column)

        # Label to show min and max range
        self.control_panel = ui.label().bind_text_from(self.min_max_range, 'value',
                          backward=lambda v: f'min: {v["min"]}, max: {v["max"]}')

        # Reset button to restore original zoom level
        ui.button("Reset Zoom", on_click=self.reset_graph)

    async def pick_dat_file(self):
        result = await app.native.main_window.create_file_dialog()
        if len(result) > 0:
            self.dat_filename = result[0]
            logger.info(f"DAT file {self.dat_filename} selected")

        try:

            # Load the dat file using polars
            self.dat_file_data = pl.read_csv(self.dat_filename, separator=" ", has_header=True)  # First line headers
            columns = [col for col in self.dat_file_data.columns if col]  # Filter out any empty column names
            logger.info(columns)

            # Update the dropdown options
            self.graph_dropdown.options = columns
            self.second_graph_dropdown.options = columns  # Update second dropdown
            self.graph_dropdown.update()  # Refresh and display the new options
            self.second_graph_dropdown.update()

            # Set the initial min and max range based on the x-axis data
            x_column = self.x_axis_dropdown.value
            x_data = self.dat_file_data[x_column].to_numpy()
            x_beginning = x_data.min()
            x_end = x_data.max()

            # Store the original range for resetting purposes
            self.original_min_max = {'min': x_beginning, 'max': x_end}

            # Set the min/max range of the control panel based on the x data
            self.min_max_range.min = x_beginning
            self.min_max_range.max = x_end
            self.min_max_range.value = {'min': x_beginning, 'max': x_end}
            self.min_max_range.update()

        except Exception as ex:
            logger.error(f"Error reading .dat file: {ex}")
            ui.notify("Error reading .dat file")

    def plot_selected_column(self):
        """Plot the selected columns from the .dat file."""

        y_column_1 = self.graph_dropdown.value  # First y-axis column
        y_column_2 = self.second_graph_dropdown.value  # Second y-axis column
        x_column = self.x_axis_dropdown.value  # x axis

        if self.dat_file_data is not None and y_column_1 in self.dat_file_data.columns:

            x_data = self.dat_file_data[x_column].to_numpy()

            # Get selected min and max values from the control panel for zooming
            zoom_min = self.min_max_range.value['min']
            zoom_max = self.min_max_range.value['max']

            y_data_1 = self.dat_file_data[y_column_1].to_numpy()

            # Create the first trace for the left y-axis
            fig = go.Figure(data=go.Scatter(x=x_data, y=y_data_1, name=y_column_1, yaxis='y1'))

            # If a second Y-axis column is selected, add it as a second trace
            if y_column_2 != "Select Graph" and y_column_2 in self.dat_file_data.columns:
                y_data_2 = self.dat_file_data[y_column_2].to_numpy()
                fig.add_trace(go.Scatter(x=x_data, y=y_data_2, name=y_column_2, yaxis='y2'))

            # Update layout to add second Y-axis on the right side
            fig.update_layout(
                title=f"Plot of {y_column_1} and {y_column_2} vs {x_column}",
                autosize=True,  # plot auto-resize
                height=None,  # height determined by the container
                yaxis=dict(
                    title=y_column_1,
                    side="left"
                ),
                yaxis2=dict(
                    title=y_column_2,
                    side="right",
                    overlaying="y",  # Overlay on the same x-axis
                    position=1  # Position the second Y-axis on the right
                ),
                xaxis=dict(
                    title=x_column,
                    range=[zoom_min, zoom_max],  # Use zoom range based on the control panel
                )
            )

            # Clear the container before adding the new plot
            self.plot_container.clear()  # Remove previous plot

            # Add the new plot
            with self.plot_container:
                ui.plotly(fig).style('width: 100%; height: 100%;')  # Make plot responsive


    def reset_graph(self):
        """Reset the graph to the original zoom range (full range)."""
        if self.original_min_max:
            # Reset the control panel range to the original min and max
            self.min_max_range.value = self.original_min_max
            self.min_max_range.update()

            # Re-plot the graph with the original range
            self.plot_selected_column()

def init_gui():
    page = MainDataPage()
    page.page_creation()

    # Start the NiceGUI app
    ui.run(native=True)


if __name__ in {"__main__", "__mp_main__"}:
    init_gui()

