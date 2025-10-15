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


### define variables used for the socket communication
set BespiceWave_connectionData(executable) ""
set BespiceWave_connectionData(debug_mode) 0
set BespiceWave_connectionData(specialization) ""
### server socket :
# set BespiceWave_connectionData(server_socket) 0
### server socket port :
set BespiceWave_connectionData(server_port) 0
### address from all connected clients :
# set BespiceWave_connectionData(clients_sockets) {}
### address from all connected client addresses :
# set BespiceWave_connectionData(full_address,$sock) [list $addr $port]
### data read from all connected clients :
# set BespiceWave_connectionData(read_data_line,$sock)

### we only communicate to 1 connected client :
# set BespiceWave_connectionData(current_client_socket)
### last read data line :
set BespiceWave_connectionData(last_read_data_line) ""

## This function must be called to set the path to the Bespice Wave executable.
proc BespiceWave_setExecutablePath { path } {
    global BespiceWave_connectionData

    set BespiceWave_connectionData(executable) $path
}

## Call this function to enable a specific behavior in BeSpice Wave. Set the value for example to "schematic_viewer"
##          to enable functions that have been developped for the integration to a schematic viewer / editor.
proc BespiceWave_setSpecialization { spec } {
    global BespiceWave_connectionData

    set BespiceWave_connectionData(specialization) $spec
}

## Set the debug mode to 1 to print debug messages to the screen.
proc BespiceWave_enableDebugMode { enable } {
    global BespiceWave_connectionData

    set BespiceWave_connectionData(debug_mode) $enable
}

## This function is called whenever the server socket receives data from BeSpice Wave.
proc BespiceWave_readDataFunction {sock} {
    global BespiceWave_connectionData

    if { $BespiceWave_connectionData(debug_mode) == 1 } {
        puts "BespiceWave_readDataFunction -->"
    }

    if {[eof $sock] || [catch {gets $sock BespiceWave_connectionData(read_data_line,$sock)}]} {
        if { $BespiceWave_connectionData(debug_mode) } {
            puts "BespiceWave_readDataFunction: closing connection $sock to bespice : $BespiceWave_connectionData(full_address,$sock)"
        }
        unset BespiceWave_connectionData(full_address,$sock)
        unset BespiceWave_connectionData(read_data_line,$sock)
        # we remove the closing socket from the list of clients
        set search_index [ lsearch $BespiceWave_connectionData(clients_sockets) $sock]   
        # puts " search_index for $sock in $BespiceWave_connectionData(clients_sockets)==> $search_index"
        if { $search_index >= 0 } { 
            set BespiceWave_connectionData(clients_sockets) [ lreplace $BespiceWave_connectionData(clients_sockets) $search_index $search_index ]
        }
        set nb [ llength $BespiceWave_connectionData(clients_sockets) ]
        if { $nb == 0 } {
            # no more clients left => communication closed
            unset BespiceWave_connectionData(clients_sockets)
            unset BespiceWave_connectionData(current_client_socket)
        } else {
            # we have another client connection => use this one
            set new_sock [lindex $BespiceWave_connectionData(clients_sockets) 0]
            if { $BespiceWave_connectionData(debug_mode) } {
                puts "BespiceWave_readDataFunction: communicating to bespice switched to new socket $new_sock"
            }
            set BespiceWave_connectionData(current_client_socket) [list $new_sock ]
        }
        close $sock

        set BespiceWave_connectionData(last_read_data_line) ""

        # puts "Clients = $bespice_server_getdata(clients)"
        # set nb [ llength $bespice_server_getdata(clients) ]
        # puts "number of Clients = $nb"

    } else {
        set BespiceWave_connectionData(last_read_data_line) $BespiceWave_connectionData(read_data_line,$sock)
        if { $BespiceWave_connectionData(debug_mode) } {
            puts "BespiceWave_readDataFunction: bespice --> $BespiceWave_connectionData(last_read_data_line)"
        }
    }
}

## This function is called as soon as bespice wave connects to the communication server.
##      It makes sure the communication over the socket connection is possible.
proc BespiceWave_serverFunction {sock addr port} {
    global BespiceWave_connectionData
    
    if { $BespiceWave_connectionData(debug_mode) == 1 } {
        puts "BespiceWave_serverFunction -->"
    }

    if { ![info exists BespiceWave_connectionData(clients_sockets)] } {
        if { $BespiceWave_connectionData(debug_mode) } {
            puts "BespiceWave_serverFunction: new connection $sock from $addr port $port"
        }
        set BespiceWave_connectionData(clients_sockets) [list $sock]
    } else {
        # we can' t handle more than one socket at once 
        #    however we put this socket to a list in case the 1st socket is closed. 
        #    we can then use the 2nd socket
        if { $BespiceWave_connectionData(debug_mode) } {
            puts "BespiceWave_serverFunction: new connection $sock from $addr port $port is stored"
        }
        lappend BespiceWave_connectionData(clients_sockets) [list $sock]
    }
    if  { ![info exists BespiceWave_connectionData(current_client_socket)] } {
        set BespiceWave_connectionData(current_client_socket) [list $sock]
    }

    set BespiceWave_connectionData(full_address,$sock) [list $addr $port]
    set BespiceWave_connectionData(read_data_line,$sock) ""

    fconfigure $sock -buffering line
    fileevent $sock readable [list BespiceWave_readDataFunction $sock]

    # this informs bespice wave that it receives it's instructions for a particular purpose. Some features will be adjusted for that.
    if { $BespiceWave_connectionData(specialization) != "" } {
        puts $sock "set_customer_specialization \"$BespiceWave_connectionData(specialization)\""
    }

    # puts "Clients = $bespice_server_getdata(clients)"
    # set nb [ llength $bespice_server_getdata(clients) ]
    # puts "number of Clients = $nb"
}

## This function must be called to start the server that will allow to communicate to BeSpice Wave.
proc BespiceWave_startServer {} {
    global BespiceWave_connectionData

    if { $BespiceWave_connectionData(debug_mode) == 1 } {
        puts "BespiceWave_startServer -->"
    }

    if { ! [info exists BespiceWave_connectionData(server_socket)] } {
        if {[catch {socket -server BespiceWave_serverFunction 0} err]} {
            # failed
            if { $BespiceWave_connectionData(debug_mode) == 1 } {
                puts "BespiceWave_startServer: failed to start TCP server"
                puts $err
            }
            return 0
        } else {
            # succeded 
            set server_socket $err
            set BespiceWave_connectionData(server_socket) $server_socket
            set assigned_port [lindex [fconfigure $server_socket -sockname] end]
            set BespiceWave_connectionData(server_port) $assigned_port
            if { $BespiceWave_connectionData(debug_mode) == 1 } {
                puts stderr "BespiceWave_startServer: success started server on TCP port: $assigned_port"
            }
            return 1
        }
        if { $BespiceWave_connectionData(debug_mode) } {
            puts "BespiceWave_startServer: failed to start TCP server"
            puts $err
        }
        return 0
    }
    return 1;
}

## This function must be called to 
##      (1) set up a Python server if necessary. This server will listen on a specific port.
##      (2) launch the BeSpice Wave executable. When launching BeSpice Wave, the port of the server must be passed as an argument.
proc BespiceWave_launchExecutable {} {
    global BespiceWave_connectionData
    global tcl_platform

    if { $BespiceWave_connectionData(debug_mode) == 1 } {
        puts "BespiceWave_launchExecutable -->"
    }

    if { [BespiceWave_startServer] == 1 } {
        if { [info exists BespiceWave_connectionData(executable)] } {
            if { [file exists $BespiceWave_connectionData(executable)] } {
                if { $tcl_platform(platform) == "windows" } {
                    set cmd "$BespiceWave_connectionData(executable) --socket localhost $BespiceWave_connectionData(server_port) >NUL 2>NUL &"
                } else {
                    set cmd "$BespiceWave_connectionData(executable) --socket localhost $BespiceWave_connectionData(server_port) >/dev/null 2>/dev/null &"
                }
                if { $BespiceWave_connectionData(debug_mode) == 1 } {
                    puts "BespiceWave_launchExecutable: cmd == $cmd"
                }
                if { $tcl_platform(platform) == "windows" } {
                    set cmd "exec $cmd"
                } else {
                    set cmd "exec $cmd"
                }
                if { [catch {eval $cmd} msg] } {
                    puts "BespiceWave_launchExecutable: failed to launch cmd == $cmd"
                    puts "BespiceWave_launchExecutable: msg == $msg"
                    return 0;
                }
                if { $BespiceWave_connectionData(debug_mode) == 1 } {
                    puts "BespiceWave_launchExecutable succeeded"
                }
                return 1
            } else {
                if { $BespiceWave_connectionData(debug_mode) == 1 } {
                    puts "BespiceWave_launchExecutable: the executable file $BespiceWave_connectionData(executable) doesn't exist"
                }
            }
        }
    }
    return 0
}

## This function returns 1 if a valid connection to a BeSpice Wave executable exists.
proc BespiceWave_checkIsConnected {} {
    global BespiceWave_connectionData

    if { [info exists BespiceWave_connectionData(current_client_socket)] } {
        if { $BespiceWave_connectionData(debug_mode) == 1 } {
            puts "BespiceWave_checkIsConnected is TRUE"
        }
        return 1;
    }
    if { $BespiceWave_connectionData(debug_mode) == 1 } {
        puts "BespiceWave_checkIsConnected is FALSE"
    }
    return 0;
}

## This function checks if the connection to BeSpice Wave has been established. If not, it returns after "timeout_ms" milliseconds.
proc BespiceWave_waitForConnection { timeout_ms } {
    global BespiceWave_connectionData

    set stop_and_wait 0
    set i 0
    set timeout_ms [expr $timeout_ms / 10]
    while { $i < 10 } {
        after $timeout_ms { set stop_and_wait 1 }
        vwait stop_and_wait
        if { $BespiceWave_connectionData(debug_mode) == 1 } {
            puts "BespiceWave_waitForConnection: checking for establiched connection ... "
        }
        if { [BespiceWave_checkIsConnected] == 1 } {
            break
        }
        set i [expr $i + 1]
    }
    unset stop_and_wait
    return [BespiceWave_checkIsConnected];
}

## This function sends a text command to BeSpice Wave. It doesn't wait for an answer.
proc BespiceWave_writeCommandDontWait { cmd } {
    global BespiceWave_connectionData

    if { [BespiceWave_checkIsConnected] == 1 } {
        if { $BespiceWave_connectionData(debug_mode) == 1 } {
            puts "BespiceWave_writeCommandDontWait: sending \"$cmd\" to $BespiceWave_connectionData(current_client_socket)"
        }
        puts $BespiceWave_connectionData(current_client_socket) $cmd
        return 1
    }
    return 0;
}

## This function sends a text command to BeSpice Wave. It waits for an answer and returns it.
proc BespiceWave_writeCommandAndWaitForAnswer { cmd } {
    global BespiceWave_connectionData

    if { [BespiceWave_checkIsConnected] == 1 } {
        if { $BespiceWave_connectionData(debug_mode) == 1 } {
            puts "BespiceWave_writeCommandAndWaitForAnswer: sending \"$cmd\" to $BespiceWave_connectionData(current_client_socket) waiting ... "
        }
        puts $BespiceWave_connectionData(current_client_socket) $cmd
        
        vwait BespiceWave_connectionData(last_read_data_line)
        if { $BespiceWave_connectionData(debug_mode) == 1 } {
            puts "BespiceWave_writeCommandAndWaitForAnswer: ... answer == $BespiceWave_connectionData(last_read_data_line)"
        }
        return $BespiceWave_connectionData(last_read_data_line)
    }
    return 0;
}

## This function queries the ststus of BeSpice Wave and returns it.
proc BespiceWave_getStatus {} {
    set res [BespiceWave_writeCommandAndWaitForAnswer "get_status"]
    return $res
}

## This function instructs BeSpice Wave to open a waveform file.
##      If a "spice_netlist_file" is specified, this file will also be read. It might be used to create additional curves.
##      The new curve names correspond to nodes that are electrically equivalent to existing nodes in the spice hierarchy.
proc BespiceWave_openFile { waveform_file {spice_netlist_file ""} } {
    set res [BespiceWave_writeCommandDontWait "open_file \"${waveform_file}\""]
    if { $spice_netlist_file != "" } {
        set res [BespiceWave_writeCommandDontWait "create_equivalent_nets \"${waveform_file}\" \"${spice_netlist_file}\""]
    }
    set res [BespiceWave_writeCommandDontWait "use_file_for_link_to_schematic \"${waveform_file}\" 1"]

    return $res
}

## This function will instruct BeSpice Wave to find and plot a curve matching "curve_name".
##          If "curve_color" is specified, thius color will be used to plot the curve. (example #ff0000 for red).
proc BespiceWave_addCurveToCurrentPlot { curve_name {curve_color ""} } {
    set res [BespiceWave_writeCommandDontWait "add_curve_to_plot_by_name * \"\" \"${curve_name}\" 0 $curve_color"]
    return res
}

## This function will instruct BeSpice Wave to find and plot a voltage curve corresponding to the spice node "hierarchical_node_name".
##          The plotted curve might have the name "V(hierarchical_node_name)" for example.
##          If "curve_color" is specified, thius color will be used to plot the curve. (example #ff0000 for red).
proc BespiceWave_addVoltageOnNodeToCurrentPlot { hierarchical_node_name {curve_color ""} } {
    set res [BespiceWave_writeCommandDontWait "add_voltage_on_spice_node_to_plot * \"\" \"${hierarchical_node_name}\" 0 $curve_color"]
    return $res
}

## This function will instruct BeSpice Wave to find and plot a current curve corresponding to the spice device "hierarchical_device_name".
##          The plotted curve might have the name "I(hierarchical_device_name)" for example.
##          If "curve_color" is specified, thius color will be used to plot the curve. (example #ff0000 for red).
proc BespiceWave_addCurrentThrougDeviceToCurrentPlot { hierarchical_device_name {curve_color ""} } {
    set res [BespiceWave_writeCommandDontWait "add_current_through_spice_device_to_plot * \"\" \"${hierarchical_device_name}\" 0 $curve_color"]
    return $res
}

## This function will instruct BeSpice Wave to open a new tab. The argument "plot_type" might take the values "analog", "digital", "synchronized", ...
proc BespiceWave_openNewPlot { plot_name {plot_type "default"} } {
    #   add_plot <plot name> <plot type> <flag new page> <flag make visible>
    set res [BespiceWave_writeCommandDontWait "add_plot \"$plot_name\" \"$plot_type\" 1 1"]
    return $res
}

