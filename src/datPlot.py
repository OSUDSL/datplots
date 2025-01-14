from nicegui import ui, app
from nicegui.events import UploadEventArguments
import os
import polars as pl
import numpy as np
import plotly.graph_objects as go
from loguru import logger
from datetime import datetime


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
        self.original_min_max = None  # store the original full range for resetting
        self.vertical_line_input = None  # input for vertical line position
        self.horizontal_line_input = None  # input for horizontal line position
        self.histogram_container = None  # container for the histogram
        self.menu = None # menu for first plot
        self.filter_zeros = None # filter out 0 val for histogram
        self.is_graph_rendered = False  # flag to check if the graph is rendered


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

        # Add a button to save the current graph as a .jpg
        ui.button("Save Graph as JPG", on_click=self.save_graph_as_jpg, icon="save")

        # Display current filename heading
        self.current_filename_label = ui.label("No file loaded").classes("text-lg font-semibold mt-2")

        # containers for plot1
        self.plot_container = ui.element('div').style('width: 100%; height: 100vh;')  # Full width, dynamic height

        # Add control panel in an expansion panel
        with ui.expansion("Control Panel", icon="settings", value=False).style(
                "background-color: #0e7af3; color: white; border-radius: 5px; padding: 5px;"
        ):
            with ui.column().style("padding: 10px;"):
                # Range slider for zooming
                self.min_max_range = ui.range(min=0, max=100, value={'min': 20, 'max': 80})
                self.min_max_range.on('change', self.plot_selected_column)

                # Display selected min and max range
                self.control_panel = ui.label().bind_text_from(
                    self.min_max_range, 'value',
                    backward=lambda v: f'min: {v["min"]}, max: {v["max"]}'
                )

                # Reset button to restore original zoom
                ui.button("Reset Zoom", on_click=self.reset_graph)

                # Horizontal layout for the remaining inputs and buttons
                with ui.row().style("margin-top: 10px;"):
                    # Input for vertical line position
                    self.vertical_line_input = ui.input("Vertical Line Position (X)").on('change',
                                                                                         self.plot_selected_column)
                    # Input for horizontal line position
                    self.horizontal_line_input = ui.input("Horizontal Line Position (Y)").on('change',
                                                                                             self.plot_selected_column)

                    # Button to reset lines
                    ui.button("Reset Lines", on_click=self.reset_lines)

        # Add a separator between the control panel and histogram plot
        ui.separator().style("margin-top: 10px; margin-bottom: 10px;")

        # container for histogram plot
        self.histogram_container = ui.element('div').style('width: 100%; height: 100vh;')

        # Add a toggle button for filtering zeros (histogram)
        self.filter_zeros = False

        def toggle_filter():
            self.filter_zeros = not self.filter_zeros
            self.plot_histogram()  # Re-plot the histogram with the new filter state
            ui.notify(f"Filtering Zeros: {'ON' if self.filter_zeros else 'OFF'}")

        ui.button("Toggle Zero Filter", on_click=toggle_filter)

        # Stats
        ui.separator().style("margin-top: 10px; margin-bottom: 10px;")
        self.stats_container = ui.column()


    def reset_lines(self):
        """Reset the vertical and horizontal lines by clearing the input fields."""
        self.vertical_line_input.value = ""  # Clear the vertical line input
        self.horizontal_line_input.value = ""  # Clear the horizontal line input
        self.vertical_line_input.update()
        self.horizontal_line_input.update()
        self.plot_selected_column()  # plot graph without the lines


    async def pick_dat_file(self):
        # Show a loading progress bar
        loading_bar = ui.linear_progress(value=0).style("margin-top: 10px;").bind_value_to(
            lambda: 1  # Sets progress to full when loaded
        )
        try:
            # Show the file dialog
            result = await app.native.main_window.create_file_dialog()

            if not result:
                # User canceled the dialog
                ui.notify("No file selected")
                return  # Exit the function

            # If a file was selected
            self.dat_filename = result[0]
            logger.info(f"DAT file {self.dat_filename} selected")

            # Clear previous plots and histograms
            self.plot_container.clear()
            self.histogram_container.clear()

            # Reset dropdowns
            self.graph_dropdown.value = "Select Graph"
            self.second_graph_dropdown.value = "Select Graph"
            self.graph_dropdown.options = []
            self.second_graph_dropdown.options = []
            self.graph_dropdown.update()
            self.second_graph_dropdown.update()

            # Reset control panel
            self.min_max_range.value = {'min': 0, 'max': 100}
            self.min_max_range.update()

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

            # Update control panel range
            self.min_max_range.min = x_beginning
            self.min_max_range.max = x_end
            self.min_max_range.value = {'min': x_beginning, 'max': x_end}
            self.min_max_range.update()

            # Auto-plot the first column or default to instructions
            if len(columns) > 0:
                self.graph_dropdown.value = columns[0]
                self.graph_dropdown.update()
                self.plot_selected_column()  # Automatically plot the first column

        except Exception as ex:
            logger.error(f"Error reading .dat file: {ex}")
            ui.notify("Error reading file")
        finally:
            # Remove the loading bar after the file is loaded / error occurs
            loading_bar.delete()


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
            y_data_2 = None

            # Create the first trace for the left y-axis
            fig = go.Figure(data=go.Scatter(x=x_data, y=y_data_1, name=y_column_1, yaxis='y1'))

            # If a second Y-axis column is selected, add it as a second trace
            if y_column_2 != "Select Graph" and y_column_2 in self.dat_file_data.columns:
                y_data_2 = self.dat_file_data[y_column_2].to_numpy()
                fig.add_trace(go.Scatter(x=x_data, y=y_data_2, name=y_column_2, yaxis='y2'))

            # Update layout to add second Y-axis on the right side
            fig.update_layout(
                template='plotly_dark',
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

            # Add vertical line if x position is provided
            if self.vertical_line_input.value:
                try:
                    x_position = float(self.vertical_line_input.value)
                    fig.add_vline(x=x_position, line_dash="dash", line_color="green")
                except ValueError:
                    logger.error("Invalid vertical line position")

            # Add horizontal line if y position is provided
            if self.horizontal_line_input.value:
                try:
                    y_position = float(self.horizontal_line_input.value)
                    fig.add_hline(y=y_position, line_dash="dash", line_color="yellow")
                except ValueError:
                    logger.error("Invalid horizontal line position")

            # Clear the container before adding the new plot
            self.plot_container.clear()  # Remove previous plot

            # Add the new plot
            with self.plot_container:
                ui.plotly(fig).style('width: 100%; height: 100%;')  # Make plot responsive

            self.is_graph_rendered = True

            #histogram plot
            self.plot_histogram(y_data_1, y_data_2)

            # Update the summary statistics after plotting
            self.update_summary_stats(y_data_1, y_data_2)




    def plot_histogram(self, y_data_1=None, y_data_2=None):
        """Plot a histogram based on the two selected Y-axis columns."""
        fig = go.Figure()

        y_column_1 = self.graph_dropdown.value
        y_column_2 = self.second_graph_dropdown.value

        if y_data_1 is None or y_data_2 is None:
            if y_column_1 in self.dat_file_data.columns:
                y_data_1 = self.dat_file_data[y_column_1].to_numpy()
            if y_column_2 in self.dat_file_data.columns:
                y_data_2 = self.dat_file_data[y_column_2].to_numpy()

        # Filter out zeros if the filter is active
        if self.filter_zeros:
            y_data_1 = y_data_1[y_data_1 != 0]
            if y_data_2 is not None:
                y_data_2 = y_data_2[y_data_2 != 0]

        # Add histogram for the first Y-axis column
        if y_data_1 is not None:
            fig.add_trace(go.Histogram(x=y_data_1, name=f"Histogram of {y_column_1}", opacity=0.7))

        # Add histogram for the second Y-axis column
        if y_data_2 is not None:
            fig.add_trace(go.Histogram(x=y_data_2, name=f"Histogram of {y_column_2}", opacity=0.7))

        # Update layout for the histogram
        title_text = f"Histogram of {y_column_1}"
        if y_column_2 != "Select Graph":
            title_text += f" and {y_column_2}"

        fig.update_layout(
            template='plotly_dark',
            title=title_text,
            xaxis_title="Y Values",
            yaxis_title="Frequency",
            barmode="overlay",  # Overlay histograms
            autosize=True,
        )

        # Clear and update the histogram container
        self.histogram_container.clear()
        with self.histogram_container:
            ui.plotly(fig).style('width: 100%; height: 100%;')


    def reset_graph(self):
        """Reset the graph to the original zoom range (full range)."""
        if self.original_min_max:
            # Reset the control panel range to the original min and max
            self.min_max_range.value = self.original_min_max
            self.min_max_range.update()

            # Re-plot the graph with the original range
            self.plot_selected_column()


    def update_summary_stats(self, y_data_1, y_data_2):
        """Update the summary statistics for the selected columns."""
        
        self.stats_container.clear()  # Clear any existing stats

        y_column_1 = self.graph_dropdown.value
        y_column_2 = self.second_graph_dropdown.value

        # Compute and display stats for the first Y-axis column
        if y_data_1 is not None:
            stats_1 = self.compute_stats(y_data_1)
            with self.stats_container:
                ui.label(f"Summary Stats for {y_column_1}:").classes("text-lg font-semibold")
                ui.label(f"Mean: {stats_1['mean']:.2f}, Median: {stats_1['median']:.2f}, "
                         f"Std Dev: {stats_1['std']:.2f}, Min: {stats_1['min']:.2f}, Max: {stats_1['max']:.2f}")

        # Compute and display stats for the second Y-axis column, if selected
        if y_data_2 is not None:
            stats_2 = self.compute_stats(y_data_2)
            with self.stats_container:
                ui.label(f"Summary Stats for {y_column_2}:").classes("text-lg font-semibold")
                ui.label(f"Mean: {stats_2['mean']:.2f}, Median: {stats_2['median']:.2f}, "
                         f"Std Dev: {stats_2['std']:.2f}, Min: {stats_2['min']:.2f}, Max: {stats_2['max']:.2f}")


    @staticmethod
    def compute_stats(data):
        """Compute basic statistics for a given data array."""
        return {
            'mean': np.mean(data),
            'median': np.median(data),
            'std': np.std(data),
            'min': np.min(data),
            'max': np.max(data)
        }

    def save_graph_as_jpg(self):
        """Save the current graph as a .jpg image."""
        if self.dat_file_data is None or not self.is_graph_rendered:
            ui.notify("No graph to save!", color="red")
            return

        try:
            # Retrieve the currently displayed figure
            y_column_1 = self.graph_dropdown.value
            y_column_2 = self.second_graph_dropdown.value
            x_column = self.x_axis_dropdown.value

            y_data_1 = self.dat_file_data[y_column_1].to_numpy()
            x_data = self.dat_file_data[x_column].to_numpy()

            fig = go.Figure(data=go.Scatter(x=x_data, y=y_data_1, name=y_column_1, yaxis='y1'))

            if y_column_2 != "Select Graph" and y_column_2 in self.dat_file_data.columns:
                y_data_2 = self.dat_file_data[y_column_2].to_numpy()
                fig.add_trace(go.Scatter(x=x_data, y=y_data_2, name=y_column_2, yaxis='y2'))

            # Add layout details
            fig.update_layout(
                template='plotly_dark',
                title=f"Plot of {y_column_1} and {y_column_2} vs {x_column}",
                autosize=True,
                xaxis=dict(title=x_column),
                yaxis=dict(title=y_column_1),
                yaxis2=dict(
                    title=y_column_2,
                    overlaying='y',
                    side='right',
                )
            )

            # Generate the filename using a timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"graph_{timestamp}.jpg"

            # Save the figure as a .jpg
            fig.write_image(filename, format="jpg")

            ui.notify(f"Graph saved as {filename}", color="green")
            logger.info(f"Graph saved as {filename}")

        except Exception as ex:
            ui.notify(f"Error saving graph: {ex}", color="red")
            logger.error(f"Error saving graph: {ex}")


def init_gui():
    page = MainDataPage()
    page.page_creation()

    #dark mode
    dark = ui.dark_mode()
    dark.enable()

    # Start the NiceGUI app
    ui.run(native=True)


if __name__ in {"__main__", "__mp_main__"}:
    init_gui()

