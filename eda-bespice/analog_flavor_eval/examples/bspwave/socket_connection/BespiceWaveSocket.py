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

import os
import sys
import socket
import select
import subprocess

class BespiceWaveInterface:

    m_executablePath = ""
    m_debugModeEnabled = False
    m_specialization = ""
    m_serverSocketPort = 0
    m_serverSocket = 0
    m_connectedClients = []
    m_newConnectedClients = []
    m_readTimeout = 3.0

    def __init__(self):
        self.m_executablePath = ""
        self.m_debugModeEnabled = False
        self.m_specialization = ""
        self.m_serverSocketPort = 0


    def setExecutablePath(self, path):
        self.m_executablePath = path

    def enableDebugMode(self, flag_enable):
        self.m_debugModeEnabled = flag_enable

    def setSpecialization(self, spec):
        self.m_specialization = spec

    def setReadTimeout(self, timeout_seconds):
        self.m_readTimeout = timeout_seconds


    ## This function must be called to start the server that will allow to communicate to BeSpice Wave.
    def startServer(self):
        if self.m_debugModeEnabled:
            print("BespiceWaveInterface::startServer -->")

        # not yet started ?
        if self.m_serverSocketPort == 0:            
            self.m_serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.m_serverSocket.bind(('', 0))
            self.m_serverSocket.listen(5)
            self.m_serverSocketPort = self.m_serverSocket.getsockname()[1]
            if self.m_debugModeEnabled:
                print("BespiceWaveInterface::launchExecutable listening on port {0}".format(self.m_serverSocketPort))
            self.m_serverSocket.setblocking(False)

        return True

    ## This function must be called to 
    ##      (1) set up a Python server if necessary. This server will listen on a specific port.
    ##      (2) launch the BeSpice Wave executable. When launching BeSpice Wave, the port of the server must be passed as an argument.
    def launchExecutable(self):
        if self.m_debugModeEnabled:
            print("BespiceWaveInterface::launchExecutable -->")

        if self.startServer():
            if os.path.exists(self.m_executablePath) :
                subprocess.Popen([self.m_executablePath,  "--socket", "localhost", "{0}".format(self.m_serverSocketPort)])
                return True
            else:
                if self.m_debugModeEnabled:
                    print("BespiceWaveInterface::launchExecutable: the executable file {0} doesn't exist.".format(self.m_executablePath))
        return False

    ## This function returns True if a valid connection to a BeSpice Wave executable exists.
    def checkIsConnected(self):
        if len(self.m_connectedClients) > 0:
            if self.m_debugModeEnabled:
                print("BespiceWaveInterface::checkIsConnected is TRUE")
            return True
        if self.m_debugModeEnabled:
            print("BespiceWaveInterface::checkIsConnected is FALSE")
        return False

    def printConnecteClientsConnections(self):
        if self.m_debugModeEnabled:
            print("BespiceWaveInterface::printConnecteClientsConnections {0} connected clients:".format(len(self.m_connectedClients)))
            for sock,addr in self.m_connectedClients:
                print("         {0}".format(addr))

    def acceptConnection(self):
        sock, addr = self.m_serverSocket.accept()
        if self.m_debugModeEnabled:
            print("BespiceWaveInterface::acceptConnection accepted connection from {0}".format(addr))
        sock.setblocking(False)
        self.m_connectedClients.append([sock, addr])
        self.m_newConnectedClients.append([sock, addr])

        self.printConnecteClientsConnections()

        try:
            data = sock.recv(1024)
        except select.error:
            return False
        except socket.error:
            return False

        if data:
            answer = data.decode('utf-8')
            answer = answer.strip()
            if self.m_debugModeEnabled:
                print("BespiceWaveInterface::acceptConnection received answer {0}".format(answer))
        return True

    def setupNewClients(self):
        if len(self.m_newConnectedClients) > 0:
            new_clients = self.m_newConnectedClients
            self.m_newConnectedClients = []
            if self.m_debugModeEnabled:
                print("BespiceWaveInterface::setupNewClients {0} new client connections are set up".format(len(new_clients)))
            if self.m_specialization != "":
                for conn in new_clients:
                    self.writeCommandToSocketAndWaitForAnswer("set_customer_specialization \"{0}\"".format(self.m_specialization), conn)
            else:
                for conn in new_clients:
                    self.writeCommandToSocketAndWaitForAnswer("get_status", conn)


    def createInputList(self):
        inputs = [self.m_serverSocket]
        for sock,addr in self.m_connectedClients:
            inputs.append(sock)
        return inputs


    ## This function checks if the connection to BeSpice Wave has been established. If not, it returns after "timeout_ms" milliseconds.
    def waitForConnection(self, timeout_sec):
        if self.m_debugModeEnabled:
            print("BespiceWaveInterface:waitForConnection: waiting for connection to server {0} ... ".format(self.m_serverSocket.getsockname()))
        inputs = self.createInputList()
        try:
            inputready,outputready,exceptready = select.select(inputs, [], [], timeout_sec)
        except select.error:
            return False
        except socket.error:
            return False
 
        for s in inputready:
            if s == self.m_serverSocket:
                self.acceptConnection()
            else:
                try:
                    data = s.recv(1024)
                except socket.error:
                    if self.m_debugModeEnabled:
                        print("BespiceWaveInterface:waitForConnection: exception occurred while reading")
                    data = 0
                if data:
                    other_answer = data.decode('utf-8')
                    other_answer = answer.strip()
                    if self.m_debugModeEnabled:
                        print("BespiceWaveInterface::waitForConnection received {0} form data socket".format(other_answer))
                else:
                    self.removeConnection(s)

        self.setupNewClients()

        return self.checkIsConnected()

    def removeConnection(self, sock):
        if self.m_debugModeEnabled:
            print("BespiceWaveInterface::removeConnection removing lost connection ...")
        sock.close()
        for conn in self.m_connectedClients:
            if conn[0] == sock:
                if self.m_debugModeEnabled:
                    print("BespiceWaveInterface::removeConnection the connection to {0} was lost".format(conn[1]))
                self.m_connectedClients.remove(conn)
        self.printConnecteClientsConnections()

    def writeCommandToSocketAndWaitForAnswer(self, cmd, conn):
        answer = ""
        cmd = cmd.strip()
        sock = conn[0]
        addr = conn[1]
        if self.m_debugModeEnabled:
            print("BespiceWaveInterface:writeCommandToSocketAndWaitForAnswer: sending \"{0}\" to {1} waiting ... ".format(cmd, addr))
        
        cmd = cmd + "\n"
        cmd_binary = cmd.encode('ascii', 'strict')
        try:
            sent = sock.send(cmd_binary) 
        except socket.error:
            if self.m_debugModeEnabled:
                print("BespiceWaveInterface:writeCommandToSocketAndWaitForAnswer: exception occurred while writing")
            self.removeConnection(sock)
            return answer

        inputs = self.createInputList()
        try:
            inputready,outputready,exceptready = select.select(inputs, [], [], self.m_readTimeout)
        except select.error:
            return answer
        except socket.error:
            return answer

        for s in inputready:
            if s == self.m_serverSocket:
                self.acceptConnection()
            else:
                try:
                    data = s.recv(1024)
                except socket.error:
                    if self.m_debugModeEnabled:
                        print("BespiceWaveInterface:writeCommandToSocketAndWaitForAnswer: exception occurred while reading")
                    data = 0
                if data:
                    if s == sock:
                        answer = data.decode('utf-8')
                        answer = answer.strip()
                        if self.m_debugModeEnabled:
                            print("BespiceWaveInterface::writeCommandToSocketAndWaitForAnswer received answer \"{0}\"".format(answer))
                    else:
                        if self.m_debugModeEnabled:
                            other_answer = data.decode('utf-8')
                            other_answer = answer.strip()
                            print("BespiceWaveInterface::writeCommandToSocketAndWaitForAnswer received \"{0}\" form other connection".format(other_answer))
                else:
                    self.removeConnection(s)
        return answer

    ## This function sends a text command to BeSpice Wave. It waits for an answer and returns it.
    def writeCommandAndWaitForAnswer(self, cmd):
        rc = False
        if self.checkIsConnected():
            conn = self.m_connectedClients[0]
            rc = self.writeCommandToSocketAndWaitForAnswer(cmd, conn)
            self.setupNewClients()

        return rc

    ## This function queries the ststus of BeSpice Wave and returns it.
    def getStatus(self):
        return self.writeCommandAndWaitForAnswer("get_status")

    ## This function instructs BeSpice Wave to open a waveform file.
    ##      If a "spice_netlist_file" is specified, this file will also be read. It might be used to create additional curves.
    ##      The new curve names correspond to nodes that are electrically equivalent to existing nodes in the spice hierarchy.
    def openFile(self, waveform_file, spice_netlist_file = ""):
        self.writeCommandAndWaitForAnswer("open_file \"{0}\"".format(waveform_file))
        if spice_netlist_file != "" :
            self.writeCommandAndWaitForAnswer("create_equivalent_nets \"{0}\" \"{1}\"".format(waveform_file, spice_netlist_file))
        return self.writeCommandAndWaitForAnswer("use_file_for_link_to_schematic \"{0}\" 1".format(waveform_file))

    ## This function will instruct BeSpice Wave to find and plot a curve matching "curve_name".
    ##          If "curve_color" is specified, thius color will be used to plot the curve. (example #ff0000 for red).
    def addCurveToCurrentPlot(self, curve_name, curve_color = ""):
        res = self.writeCommandAndWaitForAnswer("add_curve_to_plot_by_name * \"\" \"{0}\" 0 {1}".format(curve_name, curve_color))
        return res

    ## This function will instruct BeSpice Wave to find and plot a voltage curve corresponding to the spice node "hierarchical_node_name".
    ##          The plotted curve might have the name "V(hierarchical_node_name)" for example.
    ##          If "curve_color" is specified, thius color will be used to plot the curve. (example #ff0000 for red).
    def addVoltageOnNodeToCurrentPlot(self, hierarchical_node_name, curve_color = ""):
        res = self.writeCommandAndWaitForAnswer("add_voltage_on_spice_node_to_plot * \"\" \"{0}\" 0 {1}".format(hierarchical_node_name, curve_color))
        return res

    ## This function will instruct BeSpice Wave to find and plot a current curve corresponding to the spice device "hierarchical_device_name".
    ##          The plotted curve might have the name "I(hierarchical_device_name)" for example.
    ##          If "curve_color" is specified, thius color will be used to plot the curve. (example #ff0000 for red).
    def addCurrentThrougDeviceToCurrentPlot(self, hierarchical_device_name, curve_color = ""):
        res = self.writeCommandAndWaitForAnswer("add_current_through_spice_device_to_plot * \"\" \"{0}\" 0 {1}".format(hierarchical_device_name, curve_color))
        return res

    ## This function will instruct BeSpice Wave to open a new tab. The argument "plot_type" might take the values "analog", "digital", "synchronized", ...
    def openNewPlot(self, plot_name, plot_type = "default"):
        #   add_plot <plot name> <plot type> <flag new page> <flag make visible>
        res = self.writeCommandAndWaitForAnswer("add_plot \"{0}\" \"{1}\" 1 1".format(plot_name, plot_type))
        return res
 

