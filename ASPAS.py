"""
A script for calculating line positions and intensities
from scanned images of atomic spectrum photoplates.
"""
from collections import defaultdict
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import Slider
import matplotlib.pyplot as plt

from math import floor, ceil

import numpy as np
from PIL import Image, ImageTk
from scipy.interpolate import interp1d
from time import sleep
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk


class Data():
    """
    A container for the data being written to and read from line files.
    """
    def __init__(self):

        self.plate_resolution = 2400/25.4 # px/mm
        self.plate_offset = 0 # mm
        self.emission_lines = defaultdict(lambda: 0) # {position : intensity}
        self.comments = defaultdict(lambda: "") # {position : comment}

    def add_line(self, position, intensity):
        """Adds line to line dictionary."""
        self.emission_lines[position] = intensity

    def add_comment(self, position, comment):
        """Adds comment to comment dictionary."""
        self.comments[position] = comment

    def remove_line(self, position):
        """Removes line from line and comment dictionaries."""
        del self.emission_lines[position]
        if self.comments[position] != "": del self.comments[position]

    def get_positions(self):
        """Returns list of line positions."""
        return list(self.emission_lines.keys())

    def save_lines(self, name):
        """Writes saved data to line file."""
        save_file = open(name, 'w')
        save_file.write(f"Plate Resolution: {round(self.plate_resolution,3)} px/mm\n")
        save_file.write(f"Plate Offset: {self.plate_offset} mm\n")
        save_file.write(f" Position | Intensity | Comments\n")

        for pos in sorted(self.get_positions()):
            save_file.write(f" {pos/self.plate_resolution + self.plate_offset:>8.4f} "
                            f" {self.emission_lines[pos]:10.3f}  "
                            f" {self.comments[pos]}\n")

        save_file.close()

    def load_lines(self, name):
        """Reads saved data from line file."""
        self.emission_lines = defaultdict(lambda: 0)
        self.comments = defaultdict(lambda: "")
        lines_file = open(name, 'r').readlines()
        self.plate_resolution = float(lines_file[0].split()[2])
        self.plate_offset = float(lines_file[1].split()[2])

        for line in lines_file[3:]:
            p = (float(line.split()[0]) - self.plate_offset)*self.plate_resolution
            i = float(line.split()[1])
            try: c = line.split()[2]
            except: c = ""
            self.emission_lines[p] = i
            self.comments[p] = c


class Comparator(ttk.Frame):
    """
    The Comparator window the user interacts with.
    """
    def __init__(self):

        ttk.Frame.__init__(self)
        self.master.title("Atomic Spectrum Photoplate Analysis Software")

        self.file = None
        self.data = Data()

        # Window stretching configuration
        self.columnconfigure(0, weight=1)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(3, weight=1)
        self.columnconfigure(4, weight=1)
        self.columnconfigure(5, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(4, weight=1)

        self.intensity_canvas = None
        self.mirror_canvas = None
        self.mouse_offset = 0

        self.make_file_menu()
        self.make_plate_window()
        self.make_intensity_window()
        self.make_zoom_buttons()
        self.make_mirror_window()
        self.make_lines_window()
        self.pack(expand=tk.YES, fill=tk.BOTH)

    def make_file_menu(self):
        """Makes menu bar with file selection menu at top of window."""
        self.menu_bar = tk.Menu(self.master)
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Select Photoplate", command=self.get_plate_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self.kill)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.master.config(menu=self.menu_bar)

    def get_plate_file(self):
        """Propmpts user to select a plate image file."""
        self.file = tk.filedialog.askopenfilename(initialdir = ".",
                                                  title = f"Select a file",
                                                  filetypes = (("BMP files", "*.bmp*"), ("all files", "*.*")))
        self.load_plate(self.file)
        self.scan_plate(self.file)

    def kill(self):
        """Exits program."""
        try:
            self.intensity_canvas.get_tk_widget().destroy()
            self.mirror_canvas.get_tk_widget().destroy()
        except AttributeError: pass
        quit()

    def make_plate_window(self):
        """Creates viewing window for photoplate image."""
        self.int_scroll = tk.Scrollbar(self, orient=tk.HORIZONTAL)
        self.plate_canvas = tk.Canvas(self, bd=0, highlightthickness=0, relief=tk.RIDGE, cursor="cross",
                                      height=125, xscrollcommand=self.int_scroll.set)
        self.int_scroll.config(command=self.plate_canvas.xview) # Links scroll bar to plate canvas
        self.plate_canvas.grid(row=0, column=1, columnspan=4, sticky=tk.EW, pady=5, ipadx=50)
        self.int_scroll.grid(row=1, column=1, columnspan=4, sticky=tk.EW, pady=5, ipadx=50)
        self.scan_line = None
        self.plate_canvas.bind("<ButtonRelease-1>", self.redraw)
        self.int_scroll.bind("<ButtonRelease-1>", self.redraw)

    def make_intensity_window(self):
        """Creates viewing window for intensity plot."""
        self.intensity_figure = plt.figure()
        self.intensity_figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.ax1 = self.intensity_figure.add_subplot(1, 1, 1)
        self.ax1.margins(0)
        self.ax1.axis("off")
        self.intensity_canvas = FigureCanvasTkAgg(self.intensity_figure, self)
        self.intensity_canvas.get_tk_widget().grid(row=2, column=1, columnspan=4, sticky=tk.EW, pady=5, ipadx=50)
        self.scroll_label = tk.Label(self, text="0.0000 mm")
        self.scroll_label.grid(row=3, column=3, pady=5, padx=5, sticky=tk.E)

    def make_zoom_buttons(self):
        """Creates zoom buttons for controlling mirror window."""
        zoom_frame = ttk.Frame(self)
        zoom_frame.grid(row=4, column=0, sticky=tk.E)
        zoom_label = ttk.Label(zoom_frame, text="Zoom:")
        zoom_label.grid(row=0, column=0)
        ttk.Frame(self, width=75).grid(row=4, column=5) # To keep window centered.
        ZOOMS = [("x 10", 10), ("x 25", 25), ("x 50", 50), ("x 100", 100), ("x 150", 150)] # Zoom options.
        self.zoom = tk.IntVar()
        self.zoom.set(10)
        self.zoom_buttons = []

        for i in range(len(ZOOMS)):

            b = tk.Radiobutton(zoom_frame, text=ZOOMS[i][0], variable=self.zoom, value=ZOOMS[i][1])
            b.bind("<ButtonRelease-1>", self.redraw)
            b.grid(row=i+1, column=0, sticky=tk.W)
            self.zoom_buttons.append(b)

    def make_mirror_window(self):
        """Creates viewing window for mirror plot."""
        self.mirror_figure = plt.figure(figsize=(0.5,2.5))
        self.mirror_figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.ax2 = self.mirror_figure.add_subplot(1, 1, 1)
        self.ax2.margins(0)
        self.ax2.axis('off')
        self.mirror_canvas = FigureCanvasTkAgg(self.mirror_figure, self)
        self.mirror_canvas.get_tk_widget().grid(row=4, column=2, columnspan=2, sticky=tk.EW, pady=5, ipadx=5)
        self.mirror_slider_x = tk.Scale(self, from_=-3, to=3, resolution=0.01, orient=tk.HORIZONTAL)
        self.mirror_slider_x.grid(row=5, column=2, columnspan=2, sticky=tk.EW, pady=5, ipadx=5)
        self.mirror_slider_x.bind("<ButtonRelease-1>", self.redraw)
        self.mirror_slider_y = tk.Scale(self, from_=256, to=1, resolution=1, orient=tk.VERTICAL)
        self.mirror_slider_y.set(256)
        self.mirror_slider_y.bind("<ButtonRelease-1>", self.rescale_mir)
        self.mirror_slider_y.grid(row=4, column=1, sticky=tk.NS, pady=5, ipadx=5)

    def make_lines_window(self):
        """Creates window for recording line data."""
        tabs_frame = ttk.Notebook(self)
        lines_tab = ttk.Frame(tabs_frame)
        tabs_frame.add(lines_tab, text="Ruling")

        # Create buttons for reading and writing lines.
        self.add_line_button = ttk.Button(lines_tab, text="Add line", command=self.add_line)
        self.delete_line_button = ttk.Button(lines_tab, text="Delete line", command=self.delete_line)
        self.save_lines_button = ttk.Button(lines_tab, text="Save lines", command=self.save_lines)
        self.load_lines_button = ttk.Button(lines_tab, text="Load lines", command=self.load_lines)
        self.add_line_button.grid(row=0, column=0, padx=5, pady=5)
        self.delete_line_button.grid(row=0, column=1, padx=5, pady=5)
        self.save_lines_button.grid(row=0, column=2, padx=5, pady=5)
        self.load_lines_button.grid(row=0, column=3, padx=5, pady=5)

        # Comments entry.
        ttk.Label(lines_tab, text="Comments:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.comment_entry = ttk.Entry(lines_tab)
        self.comment_entry.bind("<Return>", self.add_comment)
        self.comment_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky=tk.EW)
        self.line_buttons = [self.add_line_button, self.delete_line_button,
                             self.save_lines_button, self.load_lines_button,
                             self.comment_entry]

        # DPI entry.
        ttk.Label(lines_tab, text="DPI:").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
        self.dpi_entry = ttk.Entry(lines_tab)
        self.dpi_entry.insert(0, "2400")
        self.dpi_entry.bind("<Return>", self.set_dpi)
        self.dpi_entry.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky=tk.EW)

        # Offset entry.
        ttk.Label(lines_tab, text="Offset:").grid(row=3, column=0, sticky=tk.E, padx=5, pady=5)
        self.offset_entry = ttk.Entry(lines_tab)
        self.offset_entry.insert(0, "0")
        self.offset_entry.bind("<Return>", self.set_offset)
        self.offset_entry.grid(row=3, column=1, columnspan=3, padx=5, pady=5, sticky=tk.EW)
        self.comment_notif = ttk.Label(lines_tab, text="")
        self.comment_notif.grid(row=4, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)

        tabs_frame.grid(row=4, rowspan=2, column=4, sticky=tk.NSEW, pady=5, padx=(10,0))

    def load_plate(self, plate_file):
        """Opens plate file image, rescales it, and displays it on the plate canvas."""
        self.plate_bmp = Image.open(plate_file)
        self.plate_width = self.plate_bmp.size[0]
        # Rescale image to 125 px tall for self.plate_canvas.
        if self.plate_bmp.size[1] != 125:

            self.rescaling = self.plate_bmp.size[1]/125
            self.plate_bmp = self.plate_bmp.resize((round(i/self.rescaling) for i in self.plate_bmp.size))

        self.plate_photo = ImageTk.PhotoImage(self.plate_bmp)
        self.plate_canvas.create_image(0, 0, anchor=tk.NW, image=self.plate_photo)
        self.plate_canvas.config(scrollregion=(0,0,self.plate_bmp.size[0],self.plate_bmp.size[1]))

    def scan_plate(self, plate_file):
        """Scans columns of pixles and averages their intensities, interpolating subpixle values."""
        plate_array = np.transpose(np.array(Image.open(plate_file)))
        intensity = []

        for column in plate_array:

            intensity.append(256 - np.average(column))

        # Extrapolated values aren't used. Only necessary for plotting.
        self.intensity = interp1d(range(self.plate_width), intensity, kind='cubic', fill_value='extrapolate')

    def redraw(self, event):
        """Redraws photoplate canvas, intensity plot, and mirror plot."""
        # So mirror scale and buttons don't affect event.x
        if event is not None:
            is_slider = event.widget is self.mirror_slider_x
            in_line_buttons = event.widget in self.line_buttons
            in_zoom_buttons = event.widget  in self.zoom_buttons

            if not (is_slider or in_line_buttons or in_zoom_buttons):
                self.mouse_offset = min(max(event.x/self.plate_canvas.winfo_width(),0),1) # Keeps 0 <= mouse offset <= 1
                self.mirror_slider_x.set(0) # Resets scale if plate canvas or intensity scroll bar is clicked.

        try:
            self.plate_redraw(event)
            self.int_redraw(event)

        except AttributeError:
            print("Error: No plate file selected. Unable to plot.")

    def rescale_mir(self, event):
        """Redraws mirror plot based on y-axis mirror slider."""
        self.ax2.set_ylim(bottom=0, top=self.mirror_slider_y.get())
        self.mirror_canvas.draw()

    def plate_redraw(self, event):
        """Redraws photoplate canvas."""
        if self.scan_line is not None: self.plate_canvas.delete(self.scan_line)
        # Left and right image boundaries.
        (L, R) = (min(max(i*self.plate_width,0),self.plate_width) for i in self.int_scroll.get())
        # Middle value between L and R, offset to click position and mirror slider.
        M = (L+R)/2 + (self.mouse_offset - 0.5)*(R-L) + self.mirror_slider_x.get()
        # Scan line displayed on photoplate to indicate M.
        self.scan_line = self.plate_canvas.create_line(M/self.rescaling, 0,
                                                       M/self.rescaling, self.plate_bmp.size[1],
                                                       fill="red", width=1)
        self.plate_canvas.update_idletasks # Ensures line is drawn.

    def int_redraw(self, event):
        """Redraws intensity canvas."""
        # Left and right image boundary pixel values.
        (L, R) = (min(max(i*self.plate_width,0),self.plate_width) for i in self.int_scroll.get())
        M = (L+R)/2 + (self.mouse_offset - 0.5)*(R-L) + self.mirror_slider_x.get()
        # Displays scan line position.
        self.scroll_label['text'] = f'{round(M/self.data.plate_resolution + self.data.plate_offset,4)} mm'
        px = np.arange(L, R, 0.01) # Range of pixel values to plot.
        self.ax1.clear()
        self.ax1.margins(0)
        self.ax1.plot(px, self.intensity(px), color="black", linewidth=1) # Plot intensity between L and R.
        if self.data.emission_lines != {}: # Plot any saves lines with positions between L and R.
            for pos in self.data.get_positions():
                if pos > L and pos < R:
                    self.ax1.axvline(x=pos, color="#17becf", linewidth=2)
        self.ax1.axvline(x=M, color="red", linewidth=1) # Scan line indicates position of M.
        self.intensity_canvas.draw()
        self.mir_redraw(event, L, M, R)

    def mir_redraw(self, event, Left, Mid, Right):
        """Redraws mirror canvas."""
        # Get values from self.int_redraw().
        (L, R) = Left, Right
        self.M = Mid
        W = (R-L)/self.zoom.get() # Half-width of zoomed section.
        ML, MR = round(self.M-W,2), round(self.M+W,2) # Left and right boundaries of zoomed section.
        px1 = np.arange(max(ML,L), min(MR,R), 0.01) # Section of plate to plot.
        px2 = [2*self.M - i for i in px1] # Mirror-reversed section of plate.
        self.ax2.clear()
        self.ax2.margins(0)
        self.ax2.set_ylim(bottom=0, top=self.mirror_slider_y.get())
        self.ax2.plot(px1, self.intensity(px1), color="black",   linewidth=1) # Plot zoomed section of plate.
        self.ax2.plot(px2, self.intensity(px1), color="#7f7f7f", linewidth=1) # Plot mirror-reversed zoomed section of plate.
        if self.data.emission_lines != {}: # Plot any saves lines with positions between ML and MR.
            for pos in self.data.get_positions():
                if pos > ML and pos < MR:
                    self.ax2.axvline(x=pos, color="#17becf", linewidth=2)
        self.ax2.axvline(x=self.M, color="red", linewidth=1) # Scan line indicates position of M.
        self.mirror_canvas.draw()

    def add_line(self):
        """Adds line to working data."""
        out_of_bounds = False
        if not (0 < self.M < self.plate_width):
            out_of_bounds = True

        already_in = False
        for pos in self.data.get_positions(): # Checks if line is already in data set to prevent duplicates.

            if abs(pos - self.M) < 0.1:
                alread_in = True
                continue

        if not already_in and not out_of_bounds:

            self.data.add_line(self.M, self.intensity(self.M))
            self.comment_notif.configure(text="Line added.")
            self.comment_notif.after(2000, lambda : self.comment_notif.configure(text=""))

        else:

            if already_in:
                self.comment_notif.configure(text="Error: Line already added.")
                self.comment_notif.after(2000, lambda : self.comment_notif.configure(text=""))

            if out_of_bounds:
                self.comment_notif.configure(text="Error: Line out of bounds.")
                self.comment_notif.after(2000, lambda : self.comment_notif.configure(text=""))

        self.redraw(None)

    def add_comment(self, event):
        """Adds comment to working data."""
        line = False

        for pos in self.data.get_positions():

            if abs(pos - self.M) < 0.1:

                self.data.add_comment(pos, str(self.comment_entry.get()))
                line = True
                continue

        if line is True:

            self.comment_notif.configure(text="Comment added.")
            self.comment_notif.after(2000, lambda : self.comment_notif.configure(text=""))

        else:

            self.comment_notif.configure(text="Error: Line not found.\nComment not added.")
            self.comment_notif.after(2000, lambda : self.comment_notif.configure(text=""))

    def delete_line(self):
        """Removes lines within 0.1 px of self.M from working data."""
        line = False
        for pos in self.data.get_positions():

            if abs(pos - self.M) < 0.1:

                self.data.remove_line(pos)
                line = True

        if line is True:

            self.comment_notif.configure(text="Line deleted.")
            self.comment_notif.after(2000, lambda : self.comment_notif.configure(text=""))

        else:

            self.comment_notif.configure(text="Error: No line to delete.")
            self.comment_notif.after(2000, lambda : self.comment_notif.configure(text=""))

        self.redraw(None)

    def save_lines(self):
        """Writes lines and comments within workingdata to a file."""
        self.data.save_lines(self.file[:-4] + "_lines.dat")
        self.comment_notif.configure(text="Lines saved. You may now safely exit.")
        self.comment_notif.after(2000, lambda : self.comment_notif.configure(text=""))

    def load_lines(self):
        """Reads lines and commends within file to working data."""
        self.load_file = tk.filedialog.askopenfilename(initialdir = ".",
                                             title = f"Select a file",
                                             filetypes = (("Data files", "*.dat*"), ("all files", "*.*")))
        self.data.load_lines(self.load_file)
        self.offset_entry.insert(0, self.data.plate_offset)
        self.comment_notif.configure(text="Lines loaded.\nClick plate to refresh.")
        self.comment_notif.after(2000, lambda : self.comment_notif.configure(text=""))
        self.redraw(None)

    def set_dpi(self, event):
        """Sets the resolution of the scanned plate in pixels per millimeter."""
        self.data.plate_resolution = float(self.dpi_entry.get())/25.4 # Converts DPI to px/mm
        self.comment_notif.configure(text="DPI recorded.")
        self.comment_notif.after(2000, lambda : self.comment_notif.configure(text=""))

    def set_offset(self, event):
        """Sets the offset for saved lines."""
        self.data.plate_offset = float(self.offset_entry.get())
        self.comment_notif.configure(text="Offset recorded.")
        self.comment_notif.after(2000, lambda : self.comment_notif.configure(text=""))

if __name__ == '__main__':

    Comparator().mainloop()
