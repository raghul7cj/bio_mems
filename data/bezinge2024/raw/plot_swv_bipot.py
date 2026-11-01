#!/usr/bin/env python3

# library imports
import csv
import datetime
import logging
import sys
import matplotlib.pyplot as plt
import time
import numpy as np

# Local imports
import palmsens.instrument
import palmsens.mscript
import palmsens.serial

###############################################################################
###  Start of configuration
# Run

Nswv = 22  # [-] Number of cycles for square wave voltammetry


# Location of MethodSCRIPT file to use.
mscript_pulse = 'scripts/PulseMethod.txt'
mscript_swv = 'scripts/SWVMethod.txt'

# Save file
save_file_path = datetime.datetime.now().strftime('ms_plot_%Y%m%d-%H%M%S') + '.csv'

###############################################################################

LOG = logging.getLogger(__name__)


def write_curve_to_csv(file, curve, time, n):
    
    with open(file, 'at', newline='', encoding='ascii') as f:
        # For MS Excel, add: file.write('sep=;\n')
        writer = csv.writer(f, delimiter=';')
        
        if n==0:
            writer.writerow(['index']+['TimeFromStart [s]']+['%s [%s]' % (value.type.name, value.type.unit) for value in curve[0][0]])
        
        
        for package in curve[0]:
            writer.writerow([n] + ['%.4f' % time] + [value.value for value in package])

def main():
    ### Logging configuration
    logging.basicConfig(level=logging.ERROR, format='[%(module)s] %(message)s', stream=sys.stdout)
    logging.getLogger('palmsens').setLevel(logging.INFO)

    ### Initialize variables and plot    
    tstart = time.time() # starting time of measurement
    
    plt.figure(figsize=(8, 4))  # Create a new figure with a custom size
    plt.ion()
    axes = []
    for k in [0,1]:
        ax = plt.subplot(1,2,k+1)
        ax.set_xlabel('time (V)')
        ax.set_ylabel('current (A)')
        axes.append(ax)
    
    ### Serial connection to the device:  create and open communication
    port = palmsens.serial.auto_detect_port()
    
    with palmsens.serial.Serial(port, 1) as comm:
        device = palmsens.instrument.Instrument(comm)
        device_type = device.get_device_type()
        LOG.info('Connected to %s.', device_type)

        # Flow monitoring
        print('Starting pulse sensing')
        device.send_script(mscript_pulse)
        
        # Read the result lines.
        result_lines = device.readlines_until_end()
        curve = palmsens.mscript.parse_result_lines(result_lines)
        # Save data to csv
        write_curve_to_csv(save_file_path, curve, time.time()-tstart, 0)
        
        # Plot
        yval = palmsens.mscript.get_values_by_column(curve, 1, 0)
        axes[0].plot(np.arange(0, len(yval))*0.1, yval)
 
        
        ### Measurement Loop SWV
        for n in range(Nswv):
            print('Sending SWV, %i / %i' % (n+1, Nswv))
            
            # Send the MethodSCRIPT file.
            device.send_script(mscript_swv)
            # Read the result lines.
            result_lines = device.readlines_until_end()
            curve = palmsens.mscript.parse_result_lines(result_lines)
            # Save data to csv
            write_curve_to_csv(save_file_path, curve, time.time()-tstart, n+1)
            
            # Plot
            axes[1].scatter(time.time()-tstart, max(palmsens.mscript.get_values_by_column(curve, 1, 0)))
    
            #ax.autoscale()
            plt.tight_layout()
            plt.draw()
            plt.pause(0.1)
            
            #time.sleep(260)

            
if __name__ == '__main__':
    main()
