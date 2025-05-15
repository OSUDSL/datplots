from nicegui import ui, app
import os
from loguru import logger
from appdirs import AppDirs
import toml
from src._pickDatFile import pick_dat_file
from src._plotGraphs import plot_selected_column, plot_histogram
from src._saveGraphs import save_main_plot_as_jpg,save_histogram_as_jpg


def page_creation(self):
        
        load_recent_files(self)

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
                on_change=lambda:plot_selected_column(self),  # column selection
            )

            # Dropdown for second Y-axis (column) selection
            self.second_graph_dropdown = ui.select(
                ["Select Graph"],
                value="Select Graph",
                label="Select Y-axis 2 (optional)",
                on_change=lambda:plot_selected_column(self),  # column selection
            )

            self.load_file_button = ui.dropdown_button("Load DAT file", on_click= lambda:get_path(self), icon="folder", split=True, auto_close=True)
            load_recents(self)

                

        # Add a button to save the current graph as a .jpg
        ui.button("Save Main Plot as JPG", on_click=lambda:save_main_plot_as_jpg(self), icon="save")
        
        # Display current filename heading
        self.current_filename_label = ui.label("No file loaded").classes("text-lg font-semibold mt-2")

       
        # Add control panel in an expansion panel
        with ui.expansion().style('background-color:#1f1f1f; border-radius: 10px;') as expansion:
            with expansion.add_slot('header'):
                ui.icon("settings").style("color: white; border-radius: 5px; font-size: 30px; ")
            with ui.row().style('width:100%; display:flex;'):

                # Horizontal layout for the remaining inputs and buttons
                with ui.row().style('width:100%; display:flex;'):

                    self.toggleButton = ui.button("Box Zoom \n Toggle", on_click=lambda:update_toggle_box(self)).style('flex:1; margin-top:5px;font-size:13px').props('color=dark')

                    # Input for vertical line position
                    self.vertical_line_input = ui.input("Vertical Line Position (X)").on('change',
                                                                                            lambda:plot_selected_column(self)).style('flex:2;')
                     # Input for horizontal line position
                    self.horizontal_line_input = ui.input("Horizontal Line Position (Y)").on('change',
                                                                                                lambda:plot_selected_column(self)).style('flex:2;')

                    with ui.column():
                        # Button to reset lines
                        ui.button("Reset Lines", on_click=lambda: reset_lines(self)).style('border-radius: 10px;flex:1; font-size:10px').props('color=dark')

                        # Reset button to restore original zoom
                        ui.button("Reset Zoom", on_click=lambda: reset_graph(self)).style('flex:1; text-align:center; border-radius: 10px;font-size:10px').props('color=dark')


        # containers for plot1
        self.plot_container = ui.element('div').style('width: 100%; height: 100vh;')  # Full width, dynamic height


        # Add a separator between the control panel and histogram plot
        ui.separator().style("margin-top: 5px; margin-bottom: 10px;")

        # container for histogram plot
        self.histogram_container = ui.element('div').style('width: 100%; height: 100vh;')

        # Add a toggle button for filtering zeros (histogram)
        self.filter_zeros = False

        ui.button("Save Histogram as JPG", on_click=lambda: save_histogram_as_jpg(self), icon="save")

        def toggle_filter():
            self.filter_zeros = not self.filter_zeros
            plot_histogram(self)  # Re-plot the histogram with the new filter state
            ui.notify(f"Filtering Zeros: {'ON' if self.filter_zeros else 'OFF'}")

        ui.button("Toggle Zero Filter", on_click=lambda:toggle_filter(self))

        # Stats
        ui.separator().style("margin-top: 10px; margin-bottom: 10px;")
        self.stats_container = ui.column()
    
def reset_lines(self):
    """Reset the vertical and horizontal lines by clearing the input fields."""
    self.vertical_line_input.value = ""  # Clear the vertical line input
    self.horizontal_line_input.value = ""  # Clear the horizontal line input
    self.vertical_line_input.update()
    self.horizontal_line_input.update()
    plot_selected_column(self)  # plot graph without the lines



def update_toggle_box(self):
    self.boxToggle = not self.boxToggle
    if self.boxToggle:
        self.toggleButton.props('color=dark')
    else:
        self.toggleButton.props('color=blue-10')
    plot_selected_column(self)


def load_recents(self):
    if self.load_file_button:
        self.load_file_button.clear()

    with self.load_file_button:
        ui.item(f'{self.recentFiles[0]}', on_click=lambda: pick_recent(self,0))
        ui.item(f'{self.recentFiles[1]}', on_click=lambda: pick_recent(self,1))
        ui.item(f'{self.recentFiles[2]}', on_click=lambda: pick_recent(self,2))
        ui.item(f'{self.recentFiles[3]}', on_click=lambda: pick_recent(self,3))
        ui.item(f'{self.recentFiles[4]}', on_click=lambda: pick_recent(self,4))
        
def pick_recent(self,num):
    self.recent = True
    self.dat_filename = self.recentFiles[num]
    add_new_file(self)
    pick_dat_file(self)
        
async def get_path(self):
    try:
        result = await app.native.main_window.create_file_dialog()
        # If a file was selected
        self.dat_filename = result[0]
        
        add_new_file(self)
        pick_dat_file(self)

    except Exception as ex:
        logger.error(f"Error reading .dat file: {ex}")
        ui.notify("Error reading file")

def add_new_file(self):            

    if self.dat_filename in self.recentFiles:
        self.recentFiles.remove(self.dat_filename)

    self.recentFiles.insert(0, self.dat_filename)

    if len(self.recentFiles) > 5:
        self.recentFiles.pop()

    load_recents(self)
    persist_recent_files(self)

def load_recent_files(self):
    if os.path.exists(self.filepath):
        with open(self.filepath, "r") as file:
            dataFile = toml.load(file)
            self.recentFiles[0] = dataFile["recents"]["1"]
            self.recentFiles[1] = dataFile["recents"]["2"]
            self.recentFiles[2] = dataFile["recents"]["3"]
            self.recentFiles[3] = dataFile["recents"]["4"]
            self.recentFiles[4] = dataFile["recents"]["5"]
            
def persist_recent_files(self):
    data = {
    "recents": {
        "1": f"{self.recentFiles[0]}",
        "2": f"{self.recentFiles[1]}",
        "3": f"{self.recentFiles[2]}",
        "4": f"{self.recentFiles[3]}",
        "5": f"{self.recentFiles[4]}",
    }}
               
    with open(self.filepath, 'w') as file:
        toml.dump(data, file)
    
def reset_graph(self):
    """Reset the graph to the original zoom range (full range)."""
    if self.original_min_max:
        # Reset the control panel range to the original min and max
        self.zoomMin = self.original_min_max['min']
        self.zoomMax = self.original_min_max['max']
            
        # Re-plot the graph with the original range
        plot_selected_column(self)