from nicegui import ui, app
from nicegui.events import UploadEventArguments
import os
import polars as pl
import numpy as np
import plotly.graph_objects as go
from loguru import logger
from datetime import datetime
from appdirs import AppDirs
import toml
from pathlib import Path

import webview


# Make summary look better
# Make executable? - most modern solution
# Copy to clipboard


class MainDataPage:
    def __init__(self) -> None:
        """The page is created as soon as the class is instantiated."""
        self.dat_file_data = None  # store dat file data
        self.original_min_max = None  # store the original full range for resetting
        self.filter_zeros = None  # filter out 0 val for histogram
        self.plot_figure = None
        self.plot = None
        self.range_start = None
        self.range_end = None

        self.config: dict = {}
        self.config_dir = Path(
            AppDirs("DatPlot", "DSL").user_config_dir)
        self.config_filepath = self.config_dir / Path("config.toml")

        self.gui_components: dict = {
            "graph_dropdown": None,
            "second_graph_dropdown": None,
            "x_axis_dropdown": None,
            "plot_container": None,
            "vertical_line_input": None,
            "horizontal_line_input": None,
            "histogram_container": None,
            "toggleButton": None,
            "load_file_button": None,
            "saved file": "",
            "current tab": "",
            "zero button": "",
            "summary_stats_container": None
        }

        self.bindings = {
            "current file": "No file loaded",
            "box zoom": True,
            "zoom": [0, 0],
            "graph rendered": False,
            'zero toggle': True,
            'plot range': []
        }

    def page_creation(self):

        # Create the main UI elements
        with ui.row(align_items="center").style("width:100%; display: flex;background-color:#1f1f1f; padding:10px;border-radius: 20px"):
            ui.icon("o_toys").style('font-size: 50px; flex:1;').tooltip('kachow!')

            with ui.row().style('gap: 1px'):
                with ui.row(wrap=False).style('border-radius: 20px;flex:1'):
                    # Main button with tooltip
                    with ui.button(icon='folder', on_click=self.get_path).style('width:55%;font-size:16px;'):
                        ui.tooltip('Load DAT File').classes('bg-blue')

                    # Dropdown arrow
                    menu_dropdown = ui.button(icon='arrow_drop_down').style('font-color: white; margin-left:-20px; width:2%;font-size:16px;')

                    self.gui_components["load_file_button"] = ui.menu().bind_value(menu_dropdown).props('auto-close')

                with ui.row(wrap=False).style('border-radius: 20px; flex:1; margin-left:0px'):
                    # Main button with tooltip
                    with ui.button(icon='save', on_click=self.save_current_tab).style('width:55%;font-size:16px;'):
                        ui.tooltip('Save as JPEG').classes('bg-green')

                    # Dropdown arrow
                    menu_button = ui.button(icon='arrow_drop_down').style('font-color: white; margin-left:-20px; width:2%;font-size:16px;')
                    
                    with ui.menu().props().bind_value(menu_button):
                        self.gui_components["saved file"] =  ui.row(align_items="center")
                        with self.gui_components["saved file"]:
                            ui.menu_item(f"{self.config['save plots']['path']}").style("pointer-events: none;")
                            with ui.button(icon='edit', on_click=self.get_save_path).style('align-self:center; text:center; font-size: 10px; width:10px;'):
                                ui.tooltip('Change saving location')
                            ui.separator().props('vertical')
                            self.img_select = ui.select(["PNG", "JPG", "SVG"], value="PNG")


                
            ui.separator().props('vertical')
            # Dropdown for x-axis selection (SimTime / DatTime)
            self.gui_components["x_axis_dropdown"] = ui.select(
                ["SimTime", "DatTime"],
                value="SimTime",  # Defaults to SimTime
                label="Select X-axis",
            ).style('flex:2;')

            # Dropdown for y-axis (column) selection
            self.gui_components["graph_dropdown"] = ui.select(
                ["Select Graph"],
                value="Select Graph",
                label="Select Y-axis 1",
                on_change=self.plot_selected_column,  # column selection
            ).style('flex:2;')

            ui.button(icon="compare_arrows", on_click=self.swap_y).style("width:2%").props("color=dark")

            # Dropdown for second Y-axis (column) selection
            self.gui_components["second_graph_dropdown"] = ui.select(
                ["Select Graph"],
                value="Select Graph",
                label="Select Y-axis 2 (optional)",
                on_change=self.plot_selected_column,  # column selection
            ).style('flex:2;')

            self.load_recents()

        with ui.scroll_area().classes('w-full h-[calc(100vh-9rem)]').style("display:flex"):
            # Display current filename heading
            ui.label().classes("text-lg font-semibold mt-2").bind_text_from(
                self.bindings, "current file", backward=lambda n: f"{Path(n).name}"
            )
            # containers for plot1
            
            with ui.element('div').classes('w-full').style("padding:2px; border-radius: 10px; background-color:#161616"):
                with ui.tabs(on_change=self.changeTabHandler).classes('w-full') as tabs:
                    one = ui.tab('Plot')
                    two = ui.tab('Histogram')
                    
                with ui.tab_panels(tabs, value=one).classes('w-full').style("background-color:#161616"):
                    
                    with ui.tab_panel(one).style("border-radius: 10px; background-color:#161616"):

                        with ui.row():
                            # Add control panel in an expansion panel
                            with ui.expansion().style(
                                "background-color:#1f1f1f; border-radius: 10px;"
                            ) as expansion:
                                with expansion.add_slot("header"):
                                    ui.icon("settings").style(
                                        "color: white; border-radius: 5px; font-size: 30px; "
                                    )
                                with ui.row().style("width:100%; display:flex;"):
                                    # Horizontal layout for the remaining inputs and buttons
                                    with ui.row().style("width:100%; display:flex;"):
                                        self.gui_components["toggleButton"] = (
                                            ui.button("Box Zoom \n Toggle", on_click=self.update_toggle_box)
                                            .style("flex:1; margin-top:5px;font-size:13px")
                                            .props("color=dark")
                                        )

                                        # Input for vertical line position
                                        self.gui_components["vertical_line_input"] = (
                                            ui.input("Vertical Line Pos (X)")
                                            .on("change", self.plot_selected_column)
                                            .style("flex:2; overflow: visible")
                                        )
                                        # Input for horizontal line position
                                        self.gui_components["horizontal_line_input"] = (
                                            ui.input("Horizontal Line Pos (Y)")
                                            .on("change", self.plot_selected_column)
                                            .style("flex:2;")
                                        )

                                        with ui.column():
                                            # Button to reset lines
                                            ui.button("Reset Lines", on_click=self.reset_lines).style(
                                                "border-radius: 10px;flex:1; font-size:10px"
                                            ).props("color=dark")

                                            # Reset button to restore original zoom
                                            ui.button("Reset Zoom", on_click=self.reset_graph).style(
                                                "flex:1; text-align:center; border-radius: 10px;font-size:10px"
                                            ).props("color=dark")
                            
                        self.gui_components["plot_container"] = ui.element("div").style(
                    "width: 100%; height: 650px;")  # Full width, dynamic height
                        
                        if(self.bindings['current file'] == "No file loaded"):
                            temp_x = [1, 2, 3, 4]
                            temp_y = [2, 5, 6, 10]
                            fig = go.Figure(data=go.Scatter(x=temp_x, y=temp_y, name="sim time", yaxis="y1"))

                            fig.update_layout(
                                template="plotly_dark",
                                title="Temp",
                                autosize=True,  # plot auto-resize
                                height=None,  # height determined by the container
                                yaxis=dict(
                                    title="DatTime", side="left", fixedrange=self.bindings["box zoom"]
                                ),
                                xaxis=dict(
                                    title="SimTime",
                                    rangeslider=dict(visible=True),
                                ),
                            )
                            
                            with self.gui_components["plot_container"]:
                                ui.plotly(fig).style(
                                    "width: 100%; height: 100%;"
                                )  # Make plot responsive

                    
                    
                    with ui.tab_panel(two).style("border-radius: 10px; background-color:#161616"):

                        def toggle_filter():
                            self.gui_components["zero button"].props(f'color={"blue-10" if self.bindings['zero toggle'] else "dark"}')

                            self.bindings['zero toggle'] = not self.bindings['zero toggle']
                            
                            self.plot_histogram()  # Re-plot the histogram with the new filter state
                            #ui.notify(f"Filtering Zeros: {'ON' if self.filter_zeros else 'OFF'}")

                        with ui.row():
                            #ui.button("Save Histogram as JPG", on_click=self.save_histogram_as_jpg, icon="save")
                            self.gui_components["zero button"] = ui.button("Toggle Zero Filter", on_click=toggle_filter).props("color=dark")

                        # container for histogram plot
                        self.gui_components["histogram_container"] = ui.element("div").style(
                    "width: 100%; height: 100vh;")
                        
                        if(self.bindings['current file'] == "No file loaded"):
                            self.x_data = [1, 2, 3, 4]
                            self.y_data_1 = [2, 5, 12, 10]
                            self.y_data_2 = [2, 5, 12, 10]
                            fig = go.Figure()
                            fig.add_trace(go.Histogram(x=temp_y, name=f"Histogram of temp", opacity=0.7))

                            fig.update_layout(
                                    template="plotly_dark",
                                    title="temp",
                                    xaxis_title="Y Values",
                                    yaxis_title="Frequency",
                                    barmode="overlay",  # Overlay histograms
                                    autosize=True,
                                )
                            
                            
                            with self.gui_components["histogram_container"]:
                                ui.plotly(fig).style(
                                    "width: 100%; height: 100%;"
                                )  # Make plot responsive
                        
                        # Add a toggle button for filtering zeros (histogram)
                        self.filter_zeros = False

            # Stats
            ui.separator().style("margin-top: 10px; margin-bottom: 10px;")
            
            self.gui_components["summary_stats_container"] = ui.row().classes("w-full").style("display: flex; height:30%")
            with self.gui_components["summary_stats_container"]:
                self.stats_container = ui.card().style("flex:1")
                self.zoom_stats_container = ui.card().style("flex:1")

    def swap_y(self):
        if self.gui_components["second_graph_dropdown"].value != "None":
            y2_val = self.gui_components["second_graph_dropdown"].value
            self.gui_components["second_graph_dropdown"].value = self.gui_components["graph_dropdown"].value
            self.gui_components["graph_dropdown"].value = y2_val
            self.gui_components["second_graph_dropdown"].update()
            self.gui_components["graph_dropdown"].update()



    def reset_lines(self):
        """Reset the vertical and horizontal lines by clearing the input fields."""
        self.gui_components[
            "vertical_line_input"
        ].value = ""  # Clear the vertical line input
        self.gui_components[
            "horizontal_line_input"
        ].value = ""  # Clear the horizontal line input
        self.gui_components["vertical_line_input"].update()
        self.gui_components["horizontal_line_input"].update()
        self.plot_selected_column()  # plot graph without the lines

    
    def changeTabHandler(self, e):
        if(e.value == 'Histogram'):
            self.gui_components['current tab'] = 'histogram'
            self.plot_histogram()
        else:
            self.gui_components['current tab'] = 'plot'
            self.plot_selected_column()

    def save_current_tab(self):
        if self.gui_components['current tab'] == 'histogram':
            self.save_histogram_as_jpg()
        else:
            self.save_main_plot_as_jpg()

    
    async def get_save_path(self):
        try:
            location = await app.native.main_window.create_file_dialog(allow_multiple=False, dialog_type=webview.FOLDER_DIALOG)
            if location is not None:
                self.config['save plots']['path'] = location[0]
            
                self.gui_components["saved file"].clear()

                with self.gui_components["saved file"]:
                    ui.menu_item(f"{self.config["save plots"]["path"]}")
                    ui.separator().props('vertical')
                    ui.button(icon='edit', on_click=self.get_save_path).style('align-items:center; text:center')

           
        except Exception as ex:
            logger.opt(exception=True).error(f"Error reading .dat file.")
            ui.notify("Error reading file")

    def load_recents(self):
        if self.gui_components["load_file_button"]:
            self.gui_components["load_file_button"].clear()

        with self.gui_components["load_file_button"]:
            ui.menu_item(
                f"{self.config['recent files']['recents'][0]}",
                on_click=lambda: self.pick_recent(0),
            )
            ui.menu_item(
                f"{self.config['recent files']['recents'][1]}",
                on_click=lambda: self.pick_recent(1),
            )
            ui.menu_item(
                f"{self.config['recent files']['recents'][2]}",
                on_click=lambda: self.pick_recent(2),
            )
            ui.menu_item(
                f"{self.config['recent files']['recents'][3]}",
                on_click=lambda: self.pick_recent(3),
            )
            ui.menu_item(
                f"{self.config['recent files']['recents'][4]}",
                on_click=lambda: self.pick_recent(4),
            )

    def pick_recent(self, num):
        self.bindings["current file"] = self.config["recent files"]["recents"][num]
        self.add_new_file()
        self.pick_dat_file()

    async def get_path(self):
        try:
            result = await app.native.main_window.create_file_dialog()

            # If a file was selected
            if result:
                self.bindings["current file"] = result[0]
                self.add_new_file()
                self.pick_dat_file()

        except Exception as ex:
            logger.opt(exception=True).error(f"Error reading .dat file.")
            ui.notify("Error reading file")

    def add_new_file(self):
        if self.bindings["current file"] in self.config["recent files"]["recents"]:
            self.config["recent files"]["recents"].remove(self.bindings["current file"])

        self.config["recent files"]["recents"].insert(0, self.bindings["current file"])

        if len(self.config["recent files"]["recents"]) > 5:
            self.config["recent files"]["recents"].pop()

        self.load_recents()
        self.save_config_file()


    def save_config_file(self):
        with open(self.config_filepath, "w") as file:
            toml.dump(self.config, file)

    def pick_dat_file(self):
        logger.info(f"DAT file {self.bindings["current file"]} selected")

        # Clear previous plots and histograms
        if self.gui_components["plot_container"]:
            self.gui_components["plot_container"].clear()
        if self.gui_components["histogram_container"]:
            self.gui_components["histogram_container"].clear()

        # Reset dropdowns
        self.gui_components["graph_dropdown"].value = "Select Graph"
        self.gui_components["second_graph_dropdown"].value = "Select Graph"
        self.gui_components["graph_dropdown"].options = []
        self.gui_components["second_graph_dropdown"].options = []
        self.gui_components["graph_dropdown"].update()
        self.gui_components["second_graph_dropdown"].update()

        # Load the dat file using polars
        self.dat_file_data = pl.read_csv(
            self.bindings["current file"], separator=" ", has_header=True
        )

        # Filter columns to include only ints and floats
        columns = [
            col
            for col, dtype in self.dat_file_data.schema.items()
            if dtype in [pl.Float64, pl.Int64, pl.Float32, pl.Int32]
        ]

        logger.info(f"Columns loaded: {columns}")

        # Update dropdown options
        self.gui_components["graph_dropdown"].options = columns
        self.gui_components["second_graph_dropdown"].options = ["None"] + columns
        self.gui_components["graph_dropdown"].update()
        self.gui_components["second_graph_dropdown"].update()

        # Set the initial min and max range based on the x-axis data
        x_column = self.gui_components["x_axis_dropdown"].value
        self.x_data = self.dat_file_data[x_column].to_numpy()
        x_beginning = self.x_data.min()
        x_end = self.x_data.max()

        # Store the original range for resetting
        self.original_min_max = {"min": x_beginning, "max": x_end}

        self.bindings["zoom"][0] = self.original_min_max["min"]
        self.bindings["zoom"][1] = self.original_min_max["max"]

        # Auto-plot the first column or default to instructions
        if len(columns) > 0:
            self.gui_components["graph_dropdown"].value = columns[0]
            self.gui_components["graph_dropdown"].update()
            self.plot_selected_column()  # Automatically plot the first column`

    def plot_selected_column(self):
        """Plot the selected columns from the .dat file."""

        y_column_1 = self.gui_components["graph_dropdown"].value  # First y-axis column
        y_column_2 = self.gui_components[
            "second_graph_dropdown"
        ].value  # Second y-axis column
        x_column = self.gui_components["x_axis_dropdown"].value  # x axis

        if self.dat_file_data is not None and y_column_1 in self.dat_file_data.columns:
            self.x_data = self.dat_file_data[x_column].to_numpy()

            self.y_data_1 = self.dat_file_data[y_column_1].to_numpy()
            self.y_data_2 = None

            # Create the first trace for the left y-axis
            self.plot_figure = go.Figure(
                data=go.Scatter(x=self.x_data, y=self.y_data_1, name=y_column_1, yaxis="y1")
            )

            plotTitle = f"Plot of {y_column_1} vs {x_column}"

            # If a second Y-axis column is selected, add it as a second trace
            if (
                y_column_2 != "Select Graph"
                and y_column_2 in self.dat_file_data.columns
            ):
                self.y_data_2 = self.dat_file_data[y_column_2].to_numpy()
                self.plot_figure.add_trace(
                    go.Scatter(x=self.x_data, y=self.y_data_2, name=y_column_2, yaxis="y2")
                )
                plotTitle = f"Plot of {y_column_1} and {y_column_2} vs {x_column}"

            # Update layout to add second Y-axis on the right side
            self.plot_figure.update_layout(
                template="plotly_dark",
                title=plotTitle,
                autosize=True,  # plot auto-resize
                height=None,  # height determined by the container
                yaxis=dict(
                    title=y_column_1, side="left", fixedrange=self.bindings["box zoom"]
                ),
                yaxis2=dict(
                    title=y_column_2,
                    side="right",
                    overlaying="y",  # Overlay on the same x-axis
                    position=1,  # Position the second Y-axis on the right
                ),
                xaxis=dict(
                    title=x_column,
                    range=[
                        self.bindings["zoom"][0],
                        self.bindings["zoom"][1],
                    ],  # Use zoom range based on the control panel
                    rangeslider=dict(visible=True),
                ),
            )

            # Add vertical line if x position is provided
            if self.gui_components["vertical_line_input"].value:
                try:
                    x_position = float(self.gui_components["vertical_line_input"].value)
                    self.plot_figure.add_vline(x=x_position, line_dash="dash", line_color="green")
                except ValueError:
                    logger.error("Invalid vertical line position")

            # Add horizontal line if y position is provided
            if self.gui_components["horizontal_line_input"].value:
                try:
                    y_position = float(
                        self.gui_components["horizontal_line_input"].value
                    )
                    self.plot_figure.add_hline(y=y_position, line_dash="dash", line_color="yellow")
                except ValueError:
                    logger.error("Invalid horizontal line position")

            # Clear the container before adding the new plot
            self.gui_components["plot_container"].clear()  # Remove previous plot

            # Add the new plot
            with self.gui_components["plot_container"]:
                ui.plotly(self.plot_figure).on('plotly_relayout', handler=self.handle_relayout).style(
                    "width: 100%; height: 100%;"
                )  
                # ui.plotly(self.plot_figure).style(
                #      "width: 100%; height: 100%;"
                #  )  
            
            self.bindings["graph rendered"] = True

            # histogram plot
            self.plot_histogram()

            # Update the summary statistics after plotting
            self.update_summary_stats()

  


    def plot_histogram(self):
        """Plot a histogram based on the two selected Y-axis columns."""
        fig = go.Figure()

        y_column_1 = self.gui_components["graph_dropdown"].value
        y_column_2 = self.gui_components["second_graph_dropdown"].value

        if self.y_data_1 is None or self.y_data_2 is None:
            if y_column_1 in self.dat_file_data.columns:
                self.y_data_1 = self.dat_file_data[y_column_1].to_numpy()
            if y_column_2 in self.dat_file_data.columns:
                self.y_data_2 = self.dat_file_data[y_column_2].to_numpy()

        # Filter out zeros if the filter is active
        if self.filter_zeros:
            self.y_data_1 = self.y_data_1[self.y_data_1 != 0]
            if self.y_data_2 is not None:
                self.y_data_2 = self.y_data_2[self.y_data_2 != 0]

        # Add histogram for the first Y-axis column
        if self.y_data_1 is not None:
            fig.add_trace(
                go.Histogram(x=self.y_data_1, name=f"Histogram of {y_column_1}", opacity=0.7)
            )

        # Add histogram for the second Y-axis column
        if self.y_data_2 is not None:
            fig.add_trace(
                go.Histogram(x=self.y_data_2, name=f"Histogram of {y_column_2}", opacity=0.7)
            )

        # Update layout for the histogram
        title_text = f"Histogram of {y_column_1}"
        if y_column_2 != "Select Graph":
            title_text += f" and {y_column_2}"

        fig.update_layout(
            template="plotly_dark",
            title=title_text,
            xaxis_title="Y Values",
            yaxis_title="Frequency",
            barmode="overlay",  # Overlay histograms
            autosize=True,
        )

        # Clear and update the histogram container
        self.gui_components["histogram_container"].clear()
        with self.gui_components["histogram_container"]:
            ui.plotly(fig).style("width: 100%; height: 100%;")


    def reset_graph(self):
        """Reset the graph to the original zoom range (full range)."""
        if self.original_min_max:
            # Reset the control panel range to the original min and max
            self.bindings["zoom"][0] = self.original_min_max["min"]
            self.bindings["zoom"][1] = self.original_min_max["max"]

            # Re-plot the graph with the original range
            self.plot_selected_column()

    def update_toggle_box(self):
        self.gui_components["toggleButton"].props(
            f'color={"blue-10" if self.bindings['box zoom'] else "dark"}'
        )

        self.bindings["box zoom"] = not self.bindings["box zoom"]
        self.plot_selected_column()



    def handle_relayout(self, event):
        if 'xaxis.range' in event.args:
            self.range_start = event.args['xaxis.range'][0]
            self.range_end = event.args['xaxis.range'][1]
        elif "xaxis.range[0]" in event.args:
            self.range_start = event.args['xaxis.range[0]']
            self.range_end  = event.args['xaxis.range[1]']
        self.add_zoom_stats()


    def add_zoom_stats(self):
        
        if self.range_start and self.range_end is not None:
            y_column_1 = self.gui_components["graph_dropdown"].value
            y_column_2 = self.gui_components["second_graph_dropdown"].value

            self.zoom_stats_container.clear()

            self.x_range_indices = np.where((self.x_data >= self.range_start) & (self.x_data <= self.range_end))

            new_data_y_1 = self.y_data_1[self.x_range_indices]
            
            if self.y_data_2 is not None:
                new_data_y_2 = self.y_data_2[self.x_range_indices]

            if new_data_y_1 is not None:
                stats_1 = self.compute_stats(new_data_y_1)
                with self.zoom_stats_container:
                    ui.label(f"Stats for {y_column_1} (Zoomed Region):").classes(
                        "text-lg font-semibold"
                    )

                    ui.separator()
                    
                    with ui.column().classes('w-full items-center'):
                        with ui.row(wrap=True):
                            with ui.column().classes('items-center gap-0'):
                                ui.label(f"{stats_1['mean']:.2f}").classes("text-lg gap-0")
                                ui.label("Mean").classes("font-semibold gap-0")
                                ui.separator().props('vertical')
                            with ui.column().classes('items-center gap-0'):
                                ui.label(f"{stats_1['median']:.2f}").classes("text-lg gap-0")
                                ui.label("Median").classes("font-semibold gap-0")
                            with ui.column().classes('items-center gap-0'):
                                ui.label(f"{stats_1['std']:.2f}").classes("text-lg gap-0")
                                ui.label("Std Dev").classes("font-semibold gap-0")
                            ui.separator()
                        with ui.row(wrap=False, align_items='stretch').classes('items-center'):
                            with ui.column().classes('items-center gap-0'):
                                ui.label(f"{stats_1['min']:.2f}").classes("text-lg gap-0")
                                ui.label("Min").classes("font-semibold gap-0")
                            with ui.column().classes('items-center gap-0'):
                                ui.label(f"{stats_1['max']:.2f}").classes("text-lg gap-0")
                                ui.label("Max").classes("font-semibold gap-0")
                        
                        ui.button("Copy Stats", on_click=lambda: self.copyStats(stats_1))
            

            # Compute and display stats for the second Y-axis column, if selected
            if self.y_data_2 is not None:

                stats_2 = self.compute_stats(new_data_y_2)
                with self.zoom_stats_container:
                    ui.separator()

                    # TODO FIX LATER ADD LABELS
                    ui.label(f"Stats for {y_column_2} (Zoomed Region):").classes(
                        "text-lg font-semibold"
                    )
                    ui.separator()

                    with ui.column().classes('w-full items-center'):
                        with ui.row(wrap=True):
                            with ui.column().classes('items-center gap-0'):
                                ui.label(f"{stats_2['mean']:.2f}").classes("text-lg gap-0")
                                ui.label("Mean").classes("font-semibold gap-0")
                                ui.separator().props('vertical')
                            with ui.column().classes('items-center gap-0'):
                                ui.label(f"{stats_2['median']:.2f}").classes("text-lg gap-0")
                                ui.label("Median").classes("font-semibold gap-0")
                            with ui.column().classes('items-center gap-0'):
                                ui.label(f"{stats_2['std']:.2f}").classes("text-lg gap-0")
                                ui.label("Std Dev").classes("font-semibold gap-0")
                            ui.separator()
                        with ui.row(wrap=False, align_items='stretch').classes('items-center'):
                            with ui.column().classes('items-center gap-0'):
                                ui.label(f"{stats_2['min']:.2f}").classes("text-lg gap-0")
                                ui.label("Min").classes("font-semibold gap-0")
                            with ui.column().classes('items-center gap-0'):
                                ui.label(f"{stats_2['max']:.2f}").classes("text-lg gap-0")
                                ui.label("Max").classes("font-semibold gap-0")
                        
                        ui.button("Copy Stats", on_click=lambda: self.copyStats(stats_2))
    

    def copyStats(self, stats):
        data = f"""Mean: {stats['mean']:.2f}\nMeidan: {stats['median']:.2f}\nStd Dev: {stats['std']:.2f}\nMin: {stats['min']:.2f}\nMax: {stats['max']:.2f}"""
        ui.clipboard.write(data)
        ui.notify("Stats Copied", color='green')


    def update_summary_stats(self):
        """Update the summary statistics for the selected columns."""

        self.stats_container.clear()  # Clear any existing stats

        y_column_1 = self.gui_components["graph_dropdown"].value
        y_column_2 = self.gui_components["second_graph_dropdown"].value

        # Compute and display stats for the first Y-axis column
        if self.y_data_1 is not None:
            stats_1 = self.compute_stats(self.y_data_1)
            with self.stats_container:
                ui.label(f"Stats for {y_column_1}:").classes(
                    "text-lg font-semibold"
                )
                ui.separator()

                with ui.column().classes('w-full items-center'):
                    with ui.row(wrap=True):
                        with ui.column().classes('items-center gap-0'):
                            ui.label(f"{stats_1['mean']:.2f}").classes("text-lg gap-0")
                            ui.label("Mean").classes("font-semibold gap-0")
                            ui.separator().props('vertical')
                        with ui.column().classes('items-center gap-0'):
                            ui.label(f"{stats_1['median']:.2f}").classes("text-lg gap-0")
                            ui.label("Median").classes("font-semibold gap-0")
                        with ui.column().classes('items-center gap-0'):
                            ui.label(f"{stats_1['std']:.2f}").classes("text-lg gap-0")
                            ui.label("Std Dev").classes("font-semibold gap-0")
                        ui.separator()

                    with ui.row(wrap=False, align_items='stretch').classes('items-center'):

                        with ui.column().classes('items-center gap-0'):
                            ui.label(f"{stats_1['min']:.2f}").classes("text-lg gap-0")
                            ui.label("Min").classes("font-semibold gap-0")
                        with ui.column().classes('items-center gap-0'):
                            ui.label(f"{stats_1['max']:.2f}").classes("text-lg gap-0")
                            ui.label("Max").classes("font-semibold gap-0")
            
                    ui.button("Copy Stats", on_click=lambda: self.copyStats(stats_1))

                

        # Compute and display stats for the second Y-axis column, if selected
        if self.y_data_2 is not None:
            stats_2 = self.compute_stats(self.y_data_2)
            with self.stats_container:
                ui.separator().props("color=dark, inset=False")

                ui.label(f"Stats for {y_column_2}:").classes(
                    "text-lg font-semibold"
                )
                
                ui.separator()

                with ui.column().classes('w-full items-center'):
                    with ui.row(wrap=True):
                        with ui.column().classes('items-center gap-0'):
                            ui.label(f"{stats_2['mean']:.2f}").classes("text-lg gap-0")
                            ui.label("Mean").classes("font-semibold gap-0")
                            ui.separator().props('vertical')
                        with ui.column().classes('items-center gap-0'):
                            ui.label(f"{stats_2['median']:.2f}").classes("text-lg gap-0")
                            ui.label("Median").classes("font-semibold gap-0")
                        with ui.column().classes('items-center gap-0'):
                            ui.label(f"{stats_2['std']:.2f}").classes("text-lg gap-0")
                            ui.label("Std Dev").classes("font-semibold gap-0")
                        ui.separator()
                    with ui.row(wrap=False, align_items='stretch').classes('items-center'):
                        with ui.column().classes('items-center gap-0'):
                            ui.label(f"{stats_2['min']:.2f}").classes("text-lg gap-0")
                            ui.label("Min").classes("font-semibold gap-0")
                        with ui.column().classes('items-center gap-0'):
                            ui.label(f"{stats_2['max']:.2f}").classes("text-lg gap-0")
                            ui.label("Max").classes("font-semibold gap-0")
                    
                    ui.button("Copy Stats", on_click=lambda: self.copyStats(stats_2))

       

    @staticmethod
    def compute_stats(data):
        """Compute basic statistics for a given data array."""
        return {
            "mean": np.mean(data),
            "median": np.median(data),
            "std": np.std(data),
            "min": np.min(data),
            "max": np.max(data),
        }

    def save_main_plot_as_jpg(self):
        """Save the main plot as a .jpg image."""
      
        # Generate the filename using a timestamp
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"main_plot_{timestamp}." + self.img_select.value
        path = self.config['save plots']['path']
        save_location = Path(path) / Path(filename)

        fig = self.plot_figure

        if self.bindings["box zoom"]:
            fig.update_layout(
            xaxis=dict(range=[self.range_start, self.range_end]))        
        else:
            new_data_y_1 = self.y_data_1[self.x_range_indices]

            fig.update_layout(
            xaxis=dict(range=[self.range_start, self.range_end]),
            yaxis=dict(range=[min(new_data_y_1), max(new_data_y_1)]))
          
        # Save the figure as a .jpg
        print(self.img_select.value)
        fig.write_image(save_location, format=self.img_select.value.lower())

        ui.notify(f"Main plot saved as {filename}", color="green")
        logger.info(f"Main plot saved as {filename}")


    def save_histogram_as_jpg(self):
        """Save the histogram plot as a .jpg image."""
        if self.dat_file_data is None or not self.bindings["graph rendered"]:
            ui.notify("No histogram to save!", color="red")
            return

        try:
            # Retrieve histogram data
            y_column_1 = self.gui_components["graph_dropdown"].value
            y_column_2 = self.gui_components["second_graph_dropdown"].value

            self.y_data_1 = self.dat_file_data[y_column_1].to_numpy()
            self.y_data_2 = None
            if (
                y_column_2 != "Select Graph"
                and y_column_2 in self.dat_file_data.columns
            ):
                self.y_data_2 = self.dat_file_data[y_column_2].to_numpy()

            fig = go.Figure()

            # Filter zeros if necessary
            if self.filter_zeros:
                self.y_data_1 = self.y_data_1[self.y_data_1 != 0]
                if self.y_data_2 is not None:
                    self.y_data_2 = self.y_data_2[self.y_data_2 != 0]

            # Add histogram for the first Y-axis column
            if self.y_data_1 is not None:
                fig.add_trace(
                    go.Histogram(
                        x=self.y_data_1, name=f"Histogram of {y_column_1}", opacity=0.7
                    )
                )

            # Add histogram for the second Y-axis column
            if self.y_data_2 is not None:
                fig.add_trace(
                    go.Histogram(
                        x=self.y_data_2, name=f"Histogram of {y_column_2}", opacity=0.7
                    )
                )

            # Update layout
            fig.update_layout(
                template="plotly_dark",
                title=f"Histogram of {y_column_1} and {y_column_2}",
                xaxis_title="Y Values",
                yaxis_title="Frequency",
                barmode="overlay",
            )

            # Generate the filename using a timestamp
            import datetime

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"histogram_{timestamp}." + self.img_select.value

            path = self.config['save plots']['path']
            save_location = Path(path) / Path(filename)
            # Save the figure as a .jpg
            fig.write_image(save_location, format=self.img_select.value)

            ui.notify(f"Histogram saved as {filename}", color="green")
            logger.info(f"Histogram saved as {filename}")

        except Exception as ex:
            ui.notify(f"Error saving histogram: {ex}", color="red")
            logger.error(f"Error saving histogram: {ex}")

    def load_config_file(self):
        """Load user config from TOML file, or create it with defaults if missing."""

        default_config = {
                "recent files": {
                    "recents": ["", "", "", "", ""]
                },
                "save plots" : {
                    "path" : ""
                }
            }

        if not self.config_filepath.exists():
            self.config = default_config.copy()
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_filepath, "w") as f:
                toml.dump(self.config, f)
        else:
            try:
                configdata = toml.load(self.config_filepath)
                self.config = default_config.copy()
                self.config.update(configdata)
            except Exception as ex:
                logger.error(f"Failed to load config file: {ex}")
                ui.notify("Error loading user config file", color="red")


def init_gui():
    page = MainDataPage()
    
    page.load_config_file()

    page.page_creation()

    # dark mode
    dark = ui.dark_mode()
    dark.enable()

    app.on_shutdown(shutdown_handler)

    favicon = str(Path(__file__).parent / "favicon.ico")

    # Start the NiceGUI app
    ui.run(native=True, reload=False, title="DatPlot", favicon=favicon,window_size=(1000, 654))


def shutdown_handler():
    app.shutdown()


if __name__ in {"__main__", "__mp_main__"}:
    init_gui()
