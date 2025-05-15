from nicegui import ui
import plotly.graph_objects as go
from loguru import logger

def save_main_plot_as_jpg(self):
        """Save the main plot as a .jpg image."""
        if self.dat_file_data is None or not self.is_graph_rendered:
            ui.notify("No main plot to save!", color="red")
            return

        try:
            #  the main plot data
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
            filename = f"main_plot_{timestamp}.jpg"

            # Save the figure as a .jpg
            fig.write_image(filename, format="jpg")

            ui.notify(f"Main plot saved as {filename}", color="green")
            logger.info(f"Main plot saved as {filename}")

        except Exception as ex:
            ui.notify(f"Error saving main plot: {ex}", color="red")
            logger.error(f"Error saving main plot: {ex}")


def save_histogram_as_jpg(self):
        """Save the histogram plot as a .jpg image."""
        if self.dat_file_data is None or not self.is_graph_rendered:
            ui.notify("No histogram to save!", color="red")
            return

        try:
            # Retrieve histogram data
            y_column_1 = self.graph_dropdown.value
            y_column_2 = self.second_graph_dropdown.value

            y_data_1 = self.dat_file_data[y_column_1].to_numpy()
            y_data_2 = None
            if y_column_2 != "Select Graph" and y_column_2 in self.dat_file_data.columns:
                y_data_2 = self.dat_file_data[y_column_2].to_numpy()

            fig = go.Figure()

            # Filter zeros if necessary
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

            # Update layout
            fig.update_layout(
                template='plotly_dark',
                title=f"Histogram of {y_column_1} and {y_column_2}",
                xaxis_title="Y Values",
                yaxis_title="Frequency",
                barmode="overlay",
            )

            # Generate the filename using a timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"histogram_{timestamp}.jpg"

            # Save the figure as a .jpg
            fig.write_image(filename, format="jpg")

            ui.notify(f"Histogram saved as {filename}", color="green")
            logger.info(f"Histogram saved as {filename}")

        except Exception as ex:
            ui.notify(f"Error saving histogram: {ex}", color="red")
            logger.error(f"Error saving histogram: {ex}")