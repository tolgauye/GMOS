#
#    Copyright Analog Flavor 2013-2025
#
#    All rights reserved.
#
#    This software contains proprietary and confidential information which is the
#    property of Analog Flavor and is subject to license terms.
#
#    This file may be used in accordance with the license agreement 
#    provided with the software.
#
#    This copyright notice may not be removed or altered.
#

# This file uses the interface defined in BespiceWaveSocket.py
#
#       It defines some mandatory variables like the executable path.
#       Then it uses the interface to launch the executable and to send 
#       instructions over a socket connection.  

import os
import sys
import time
import BespiceWaveSocket

# this loads the implementation of the interface
bspwave = BespiceWaveSocket.BespiceWaveInterface()

# this path will be used to create absolute names for the example files
script_path = ""
if len(sys.argv):
    script_path = sys.argv[0]
    script_path = os.path.abspath(script_path)
    script_path = os.path.dirname(script_path)

# define the path of the executable
if sys.platform.startswith('win'):
    bspwave.setExecutablePath("../../../bin/bspwave.exe")
elif sys.platform.startswith('darwin'):
    bspwave.setExecutablePath("../MacOS/BeSpiceWave")
else:
    bspwave.setExecutablePath("../../../bin/bspwave")

if sys.platform.startswith('darwin'):
    waveform_file = "{0}/fourbitadder.spi3".format(script_path)
    spice_netlist_file = "{0}/fourbitadder.cir".format(script_path)
    waveform_file_2 = "{0}/example_2.csv".format(script_path)
else:
    waveform_file = "{0}/../example/fourbitadder.spi3".format(script_path)
    spice_netlist_file = "{0}/../example/fourbitadder.cir".format(script_path)
    waveform_file_2 = "{0}/../example/example_2.csv".format(script_path)

# Enable the debug mode if something goes wrong ...
#bspwave.enableDebugMode(1)
# This will enable features used for linking to a schematic editor / viewer
bspwave.setSpecialization("schematic_viewer")
bspwave.setReadTimeout(1.0);

# - starts a Python socket server
# - launches BeSpice Wave
# - instructs BeSpice Wave to connect to the server
if bspwave.launchExecutable() == False:
    print("Failed to launch BeSpice Wave executable")
    exit(1)


# waits for BeSpice Wave to connect to the server (with timeout)
if bspwave.waitForConnection(10.0) == False:
    print("Socket connection tp BeSpice Wave wasn't established after 10 seconds.")
    exit(1)

# sends commands to BeSpice Wave
bspwave.openFile(waveform_file_2)
bspwave.openFile(waveform_file, spice_netlist_file)

# these commands refer to the last opened file
bspwave.addVoltageOnNodeToCurrentPlot("x1.x1.x1.10")
bspwave.addVoltageOnNodeToCurrentPlot("x1.x1.x2.10", "#ff0000")

bspwave.addCurrentThrougDeviceToCurrentPlot("vin1a")
bspwave.addCurrentThrougDeviceToCurrentPlot("vin1b","#ffff00")

# re-open the file
bspwave.openFile(waveform_file_2)

bspwave.openNewPlot("new page 1")
# this command refer to the last opened file which is "waveform_file_2" now
bspwave.addCurveToCurrentPlot("meas","#00ffff")


# we wait until the connection is closed
while True:        
    if bspwave.checkIsConnected() == False:
        print("Connection to BeSpice Wave was closed.")
        exit(0)

    bspwave.getStatus()

    time.sleep(1.0);


