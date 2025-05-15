from nicegui import ui
import numpy as np
import plotly.graph_objects as go
from loguru import logger

def plot_selected_column(self):
        """Plot the selected columns from the .dat file."""

        if self.graph_dropdown is not None:
            y_column_1 = self.graph_dropdown.value  # First y-axis column
        
        if self.second_graph_dropdown is not None:
            y_column_2 = self.second_graph_dropdown.value  # Second y-axis column
        
        if self.x_axis_dropdown is not None:
            x_column = self.x_axis_dropdown.value  # x axis

        if self.dat_file_data is not None and y_column_1 in self.dat_file_data.columns:

            x_data = self.dat_file_data[x_column].to_numpy()

            # Get selected min and max values from the control panel for zooming
            # self.zoom_min = self.min_max_range.value['min']
            # self.zoom_max = self.min_max_range.value['max']

            y_data_1 = self.dat_file_data[y_column_1].to_numpy()
            y_data_2 = None

            # Create the first trace for the left y-axis
            fig = go.Figure(data=go.Scatter(x=x_data, y=y_data_1, name=y_column_1, yaxis='y1'))

            plotTitle = f"Plot of {y_column_1} vs {x_column}" 

            # If a second Y-axis column is selected, add it as a second trace
            if y_column_2 != "Select Graph" and y_column_2 in self.dat_file_data.columns:
                y_data_2 = self.dat_file_data[y_column_2].to_numpy()
                fig.add_trace(go.Scatter(x=x_data, y=y_data_2, name=y_column_2, yaxis='y2'))
                plotTitle = f"Plot of {y_column_1} and {y_column_2} vs {x_column}" 


            # Update layout to add second Y-axis on the right side
            fig.update_layout(
                template='plotly_dark',
                title=plotTitle,
                autosize=True,  # plot auto-resize
                height=None,  # height determined by the container
                yaxis=dict(
                    title=y_column_1,
                    side="left",
                    fixedrange=self.boxToggle
                ),
                yaxis2=dict(
                    title=y_column_2,
                    side="right",
                    overlaying="y",  # Overlay on the same x-axis
                    position=1  # Position the second Y-axis on the right
                ),
                xaxis=dict(
                    title=x_column,
                    range=[self.zoomMin, self.zoomMax],  # Use zoom range based on the control panel
                    rangeslider=dict(
                        visible=True)
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
            plot_histogram(self,y_data_1, y_data_2)

            # Update the summary statistics after plotting
            update_summary_stats(self,y_data_1, y_data_2)


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


def update_summary_stats(self, y_data_1, y_data_2):
    """Update the summary statistics for the selected columns."""
        
    self.stats_container.clear()  # Clear any existing stats

    if self.graph_dropdown is not None:
        y_column_1 = self.graph_dropdown.value
    if self.second_graph_dropdown is not None:
        y_column_2 = self.second_graph_dropdown.value

    # Compute and display stats for the first Y-axis column
    if y_data_1 is not None:
        stats_1 = compute_stats(y_data_1)
        with self.stats_container:
            ui.label(f"Summary Stats for {y_column_1}:").classes("text-lg font-semibold")
            ui.label(f"Mean: {stats_1['mean']:.2f}, Median: {stats_1['median']:.2f}, "
                     f"Std Dev: {stats_1['std']:.2f}, Min: {stats_1['min']:.2f}, Max: {stats_1['max']:.2f}")

        # Compute and display stats for the second Y-axis column, if selected
    if y_data_2 is not None:
        stats_2 = compute_stats(y_data_2)
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