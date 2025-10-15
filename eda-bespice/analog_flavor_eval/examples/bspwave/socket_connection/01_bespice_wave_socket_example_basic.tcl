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

# This file uses the interface defined in BespiceWaveSocket.tcl
#
#       It defines some mandatory variables like the executable path.
#       Then it uses the interface to launch the executable and to send 
#       instructions over a socket connection.  


# this loads the implementation of the interface
source BespiceWaveSocket.tcl

# this path will be used to create absolute names for the example files
set script_path [ file dirname [ file normalize [ info script] ] ] 

if { $tcl_platform(platform) == "windows" } {
    BespiceWave_setExecutablePath "../../../bin/bspwave.exe"
} elseif { $tcl_platform(os) == "Darwin" } {
    BespiceWave_setExecutablePath "../MacOS/BeSpiceWave"
} else {
    BespiceWave_setExecutablePath "../../../bin/bspwave"
}

# Enable the debug mode if something goes wrong ...
#BespiceWave_enableDebugMode 1
# This will enable features used for linking to a schematic editor / viewer
BespiceWave_setSpecialization "schematic_viewer"

if { $tcl_platform(os) == "Darwin" } {
    set waveform_file "${script_path}/fourbitadder.spi3"
    set spice_netlist_file "${script_path}/fourbitadder.cir"
    set waveform_file_2 "${script_path}/example_2.csv"
} else {
    set waveform_file "${script_path}/../example/fourbitadder.spi3"
    set spice_netlist_file "${script_path}/../example/fourbitadder.cir"
    set waveform_file_2 "${script_path}/../example/example_2.csv"
}

# - starts a TCL socket server
# - launches BeSpice Wave
# - instructs BeSpice Wave to connect to the server
if { ! [BespiceWave_launchExecutable] } {
    puts "Failed to launch BeSpice Wave executable"
    exit 1
}

# waits for BeSpice Wave to connect to the server (with timeout)
if { ! [BespiceWave_waitForConnection 10000] } {
    puts "Socket connection tp BeSpice Wave wasn't established after 10 seconds."
    exit 1
}

# sends commands to BeSpice Wave
BespiceWave_openFile $waveform_file_2
BespiceWave_openFile $waveform_file $spice_netlist_file

# these commands refer to the last opened file
BespiceWave_addVoltageOnNodeToCurrentPlot "x1.x1.x1.10"
BespiceWave_addVoltageOnNodeToCurrentPlot "x1.x1.x2.10" "#ff0000"

BespiceWave_addCurrentThrougDeviceToCurrentPlot "vin1a"
BespiceWave_addCurrentThrougDeviceToCurrentPlot "vin1b" "#ffff00"

# re-open the file
BespiceWave_openFile $waveform_file_2

BespiceWave_openNewPlot "new page 1"
# this command refer to the last opened file which is "waveform_file_2" now
BespiceWave_addCurveToCurrentPlot "meas" "#00ffff"

# we wait until the connection is closed
proc read_status_while_connected {} {
        
    if { [BespiceWave_checkIsConnected] == 0 } {
        puts "Connection to BeSpice Wave was closed"
        exit 0
    }

    BespiceWave_getStatus

    after 1000 {
        read_status_while_connected
    }
}

after 1000 {
    read_status_while_connected
}

vwait forever

