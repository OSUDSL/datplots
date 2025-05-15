from nicegui import ui, app
from appdirs import AppDirs
import toml
import os
from loguru import logger
from pathlib import Path


class MainDataPage:
    from src._createPage import page_creation
    from src._pickDatFile import pick_dat_file
    from src._plotGraphs import plot_selected_column, plot_histogram
    from src._saveGraphs import save_main_plot_as_jpg, save_histogram_as_jpg

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
        self.zoomMax = None
        self.zoomMin = None
        self.boxToggle = True
        self.toggleButton = None
        self.load_file_button = None
        self.dat_filename = ""
        self.recent = False
        self.recent_num = -1
        self.recentFiles = ['','','','','']
        self.dir_loc = ""
        self.recents_fileName = ""
        self.filepath = ""

        self.dir_loc = Path(AppDirs("DatPlot", "DSL").user_config_dir)
        self.recents_fileName = 'recent_history.toml'
        self.filepath = self.dir_loc / Path(self.recents_fileName)
        self.dir_loc.mkdir(parents=True, exist_ok=True)
        logger.warning("Creating directory for recents file: " + str(self.dir_loc))