# ASPAS

About:

Atomic Spectrum Photoplate Analysis Software (ASPAS) is a tool to enable the study of scanned
copies of atomic spectrum photoplates from NIST’s archive, eliminating the need for a Comparator
(Tompkins, 1951). After choosing a bitmap of a photoplate, you can specify the DPI the image
was scanned with, record the positions and intensities of emission lines on the photoplate, save
recorded data in a text file, and specify an offset for the positions of these lines.

ASPAS was written by Noah Zuckman under the Montgomery College Internship program.

Dependencies:

The program is written in Python 3. The following modules must be installed before using ASPAS:

 matplotlib
 numpy
 PIL
 scipy
 tkinter

Loading plates:

Click “Select Photoplate” from the File drop-down menu in the upper left corner.
Select a bitmap of a photoplate using the file browser that opens. A section of the photoplate will
appear at the top of the window. The scroll bar is used to navigate along the window and display
different sections of the photoplate. Click the photoplate or the scroll bar to initialize the scan
line and display the line profiles currently in view on the photoplate window. The line profiles are
graphed on the center window. Each column of pixels in the bitmap is measured for an average
intensity. Cubic interpolation is performed using interp1d from the scipy module to achieve
sub-pixel accuracy. A red scan line will appear to indicate where you clicked on the photoplate:

Adding, Saving, Loading, and Deleting Lines:

The red scan line indicates where a new line will be recorded. The mirror window in the bottom
left corner is used to ensure the scan line is centered on the peak of the line profile. It displays
a magnified section of the plate surrounding the scan line, with its mirror image superimposed in
gray, as well as a zoom control panel and y-axis slider to the left. The x-axis slider beneath the
window is used to precisely adjust the scan line’s position after getting it close to the center of a
line profile by clicking the photoplate.

Click “Add line” on the bottom right panel to record the position and intensity of this line. A
blue line will appear where you have marked this line profile’s center, indicating that it has been
added to the line list.

A comment can be added to a line when the scan line is directly overlapping it. Type a comment
into the “Comments:” entry and press the Enter key to add it to the line. Similarly, a line can be
deleted by clicking “Delete line” when the scan line is overlapping it. Clicking “Save lines” will
produce a text file detailing the positions, intensities, and comments made on recorded lines. This
text file can be loaded back into ASPAS during a later session by clicking “Load lines,” and will
show the locations of lines as previously saved.
