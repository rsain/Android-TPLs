__author__ = 'rsain'

'''
This script processes pcap files (generated by tcpdump) to compute the number of packages and bytes transmitted over the network.
This script generates a CSV file containing for all pcap files in a folder the number of packages and bytes transmitted.
Note that the Python script collectNetworkMemoryAndCPU obtains pcap files associated to Android apps while playing a scenario.
'''

import subprocess
from subprocess import check_output
import os
import math
import numpy
from pandas import *
import pandas as pd
import natsort

SDKTYPE = "CrashReporting"
DATA_FOLDER = '/Experiments/' + SDKTYPE '/data/' #Folder containing the pcap files
OUTPUT_FOLDER = '/Experiments/' + SDKTYPE + '/results/' #Folder where the CSV files are going to be saved
OUTPUT_FILE_FOR_STATS_FOR_EACH_RUN = 'networkByRun.csv' #Filename for the CSV file containing the information for each run
RUNS = 30

# Function to get number of bytes (if the input is 1kB the output is 1024 bytes)
def convertBytesConsideringUnits(value, units):
    result = 0.0

    units = units.strip()

    if units == "bytes":
        result = value
    elif units == "kB":
        result = value * 1024
    elif units == "MB":
        result = value * 1048576
    elif units == "GB":
        result = value * 1073741824
    elif units == "TB":
        result = value * 1099511627776
    else:
        print("Error: this unit (" + str(units) + ") for bytes is not handled by my code.")

    return result


# Function to get number of packets (if the input is 1k the output is 1000)
def convertPacketsConsideringUnits(value, units):
    result = 0.0

    if units == "":
        result = value
    elif units == "k":
        result = value * 1000
    elif units == "M":
        result = value * 1e6
    else:
        print("Error: this unit (" + str(units) + ") for packets is not handled by my code.")

    return result


# Dataframe containing the stats for each run and app
dfStatsForEachRun = DataFrame.from_items([
    ('SdkName', []),
    ('SdkType', []),
    ('Run', []),
    ('Packets', []),
    ('Bytes', [])
])

# Initilize variables
minNumberOfPackets = 1e10
maxNumberOfPackets = 0
accumulatedBytes = 0
minNumberOfBytes = 1e10
maxNumberOfBytes = 0

runsForApp = dict()
appsPossiblyInvalid = list()
appsPCAPFileCorrupted = list()
appsPCAPFileEmpty = list()

# Loop for each pcap file in the folder
for file in natsort.natsorted(os.listdir(DATA_FOLDER)):
    if os.path.isdir(DATA_FOLDER + file):
        continue

    fileName, fileExtension = os.path.splitext(file)
    appName = fileName.split('-')[0]
    run = fileName.split('-')[1].split('.')[0]

    if int(run) > int(RUNS):
        continue

    if fileExtension == '.pcap':
        #Check if the pcap file is empty (possibly the wifi connection was lost)
        if os.stat(DATA_FOLDER + file).st_size > 0:
            print("Processing network file '" + fileName + ".pcap' ...")
            
            # Read the network file (reads the number of bytes received and sent)
            try:
                output = check_output("tshark -r " + DATA_FOLDER + fileName + ".pcap -q -z conv,ip", shell=True,
                                      universal_newlines=True)
            except subprocess.CalledProcessError as e:
                output = "error"

            #Check if the pcap file is not corrupted (possibly the wifi connection was lost)
            if output.find("error") == -1:                                        
                if appName in runsForApp:
                    runsForApp[appName] += 1
                else:
                    runsForApp[appName] = 1

                #Read the network file (reads the number of packets and the number of bytes)
                try:
                    output = check_output("capinfos -cd \"" + DATA_FOLDER + fileName + ".pcap\"", shell=True,
                                          universal_newlines=True)
                except subprocess.CalledProcessError as e:
                    output = (e.output)
                
                networkData = output.strip().split("\n")

                packetsInformation = networkData[1].split(":")[1].strip().split(" ")                    
                if len(packetsInformation) == 1:
                    packetsValue = int(packetsInformation[0].replace(',',''))
                    packetsUnit = ""
                else:
                    packetsValue = int(packetsInformation[0])
                    packetsUnit = packetsInformation[1]
                packets = convertPacketsConsideringUnits(packetsValue, packetsUnit)
                if packets < minNumberOfPackets:
                    minNumberOfPackets = packets
                if packets > maxNumberOfPackets:
                    maxNumberOfPackets = packets
                
                bytesInformation = networkData[2].split(":")[1].strip().split(" ")
                bytesValue = int(bytesInformation[0].replace(',',''))
                bytesUnit = bytesInformation[1]
                bytes = convertBytesConsideringUnits(bytesValue, bytesUnit)
                if bytes < minNumberOfBytes:
                    minNumberOfBytes = bytes
                if bytes > maxNumberOfBytes:
                    maxNumberOfBytes = bytes
                print("Network file '" + file + "' processed successfully.")

                # A new row is inserted in the output dataframe containing the stats for each run
                dfStatsForEachRun.loc[len(dfStatsForEachRun) + 1] = [appName, SDKTYPE,
                                                                     run,
                                                                     packets,
                                                                     bytes]
            else: #the current pcap file is corrupted (possibly because the wifi connection was lost)
                appsPCAPFileCorrupted.append(fileName)                
        else:
            appsPCAPFileEmpty.append(fileName)

#Generates the CSV files
dfStatsForEachRun.to_csv(OUTPUT_FOLDER + OUTPUT_FILE_FOR_STATS_FOR_EACH_RUN, index=False)

print(dfStatsForEachRun)

#Print the list of runs which has a corrupted pcap file
if len(appsPCAPFileCorrupted) > 0:
    print("The following " + str(len(appsPCAPFileCorrupted)) + " run(s) had an incorrect pcap file:")
    print(appsPCAPFileCorrupted)

#Print the list of runs which has an empty pcap file
if len(appsPCAPFileEmpty) > 0:
    print("The following " + str(len(appsPCAPFileEmpty)) + " run(s) had an empty pcap file:")
    print(appsPCAPFileEmpty)

print("DONE!")
