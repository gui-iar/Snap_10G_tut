#!/usr/bin/env python2.7.18
'''
This code demonstrates the readout of a SNAP spectrometer with four inputs and 256 channels each (fir+fft pts), using BRAMs and the 10GB interface. 
You need a SNAP with:
The modelsim slx model and code is modifieded from the original SNAP CASPER spectrometer and 10G tutorials.
-- A 10 MHz, 8dBm reference going into the SYNTH_OSC SMA (3rd SMA from the left) and a 10G SFP+ cable with a PC adapter.
-- A test tone, noise source (or a radio telescope signal if available) going into the ADC0 to ADC3 inputs.
casperfpga                         0.1.2
Modelsim compiled with m2021a branch
Vivado/2021.1
matlab 2021a
'''


import casperfpga
import casperfpga.snapadc
import time
import numpy
import struct
import sys
import logging
import pylab
import matplotlib
import socket
from datetime import datetime

## To be set frpm local PC
fabric_port = 10000 # udp port to be used, also present in the modelsim slx design
# PC NIC MAC: 68:05:ca:d4:81:74
mac_base = int((104 << 40) + (5 << 32) + (202 << 24) + (212 << 16) + (129 << 8) + 91)  # Build PC NIC MAC ADDER DEC to HEX: 104:05:202:212:129:91 (116 hex(74) => 91 + 25(fix base))
ip_base = 192*(2**24) + 168*(2**16) + 1*(2**8) + 25 # IP PIC NIC
tx_core_name = 'Gbe0_gbe0'

# DO NOT CHANGE THESE THREE VALUES!!!
mac_location = 0x0c
ip_location = 0x14
port_location = 0x30
#####################

katcp_port = 7147
freq_range_mhz = numpy.linspace(0., 250., 256)



def get_pow_stokes():
    # get the data...same as casper tutorial
    acc_n = fpga.read_uint('acc_cnt')
    sa_0 = struct.unpack('>256L', fpga.read('Stokes_1_i_pow_1', 256*4, 0))
    sa_1 = struct.unpack('>256L', fpga.read('Stokes_1_r_pow_1', 256*4, 0))
    sb_0 = struct.unpack('>256L', fpga.read('Stokes_1_i_pow_2', 256*4, 0))
    sb_1 = struct.unpack('>256L', fpga.read('Stokes_1_r_pow_2', 256*4, 0))

    interleave_sa = []
    interleave_sb = []
    interleave_sc = []
    interleave_sd = []

    for i in range(256):
        interleave_sa.append(sa_0[i] % 2**32)
        interleave_sb.append(sa_1[i] % 2**32)
        interleave_sc.append(sb_0[i] % 2**32)
        interleave_sd.append(sb_1[i] % 2**32)

    return acc_n, numpy.array(interleave_sa, dtype=numpy.float), numpy.array(interleave_sb, dtype=numpy.float), numpy.array(interleave_sc, dtype=numpy.float), numpy.array(interleave_sd, dtype=numpy.float)


def plot_stokes():
    # plot the data...same as casper tutorial
    matplotlib.pyplot.clf()
    acc_n, interleave_sa, interleave_sb, interleave_sc, interleave_sd = get_pow_stokes()

    interleave_sa = 10*numpy.log10(interleave_sa)
    interleave_sb = 10*numpy.log10(interleave_sb)
    interleave_sc = 10*numpy.log10(interleave_sc)
    interleave_sd = 10*numpy.log10(interleave_sd)

    matplotlib.pylab.plot(freq_range_mhz, interleave_sa)
    matplotlib.pylab.plot(freq_range_mhz, interleave_sb)
    matplotlib.pylab.plot(freq_range_mhz, interleave_sc)
    matplotlib.pylab.plot(freq_range_mhz, interleave_sd)

    matplotlib.pylab.title('Integration number %i.' % acc_n)
    matplotlib.pylab.ylabel('Power (dB)')
    matplotlib.pylab.grid()
    matplotlib.pylab.xlabel('Freq (MHz)')
    matplotlib.pylab.ylim(0, 100)
    matplotlib.pylab.xlim(freq_range_mhz[0], freq_range_mhz[-1])
    fig1.canvas.draw()
    fig1.canvas.manager.window.after(100, plot_stokes)


# START OF MAIN:

if __name__ == '__main__':
    from optparse import OptionParser

    p = OptionParser()
    p.set_usage('spectrometer.py <ROACH_HOSTNAME_or_IP> [options]')
    p.set_description(__doc__)
    p.add_option('-l', '--acc_len', dest='acc_len', type='int', default=(2*(2**27)/2048),
                 help='Set the number of vectors to accumulate between dumps. default is 2*(2^28)/2048, or just under 2 seconds.')
    p.add_option('-s', '--skip', dest='skip', action='store_true',
                 help='Skip reprogramming the FPGA and configuring EQ.')
    p.add_option('-b', '--fpg', dest='fpgfile', type='str', default='',
                 help='Specify the fpg file to load')
    opts, args = p.parse_args(sys.argv[1:])

    if args == []:
        print('Please specify a SNAP board. Run with the -h flag to see all options.\nExiting.')
        exit()
    else:
        snap = args[0]

try:

    print('Connecting to server %s on port %i... ' % (snap, katcp_port)),
    fpga = casperfpga.CasperFpga(snap)
    time.sleep(2)

    if fpga.is_connected():
        print('ok\n')
    else:
        print('ERROR connecting to server %s on port %i.\n' %
              (snap, katcp_port))
        exit_fail()

    print('------------------------')
    if not opts.skip:
        bitstream = 'x4_256ch_10g_v1_2024-07-03_1342.fpg'

        print('Programming FPGA with %s...' % bitstream,)
        sys.stdout.flush()
        fpga.upload_to_ram_and_program(bitstream)
        print('done')
    else:
        print('Skipped.')

    # After programming we need to configure the ADC. The following function call assumes that
    # the SNAP has a 10 MHz reference connected. It will use this reference to generate an 500 MHz
    # sampling clock. The init function will also tweak the alignment of the digital lanes that
    # carry data from the ADC chips to the FPGA, to ensure reliable data capture. It should take about
    # 30 seconds to run.
    adc = casperfpga.snapadc.SNAPADC(fpga, ref=10)  # reference at 10MHz
    # We want a sample rate of 500 Mhz, with 2 channel per ADC chip, using 8-bit ADCs
    # (there is another version of the ADC chip which operates with 12 bits of precision)
    # if not opts.skip:
    print('Attempting to initialize ADC chips...')
    sys.stdout.flush()
    # try initializing a few times for good measure in case it fails...
    done = False
    if not opts.skip:
        for i in range(3):
            if adc.init(samplingRate=500, numChannel=2) == 0:
                done = True
                break
        print('done (took %d attempts)' % (i+1))
        if not done:
            print('Failed to calibrate after %d attempts' % (i+1))
            exit_clean()
    else:
        print('ADC - Skipped.')

    adc.selectADC([0, 1])  # send commands to the first and second ADC chip
    # Interleave four ADCs all pointing to the first and econd input
    adc.adc.selectInput([1, 1, 2, 2])
    time.sleep(1)
    print('Configuring accumulation period...')
    sys.stdout.flush()

    print('Board Clk ', fpga.estimate_fpga_clock())
    fpga.write_int('acc_len', opts.acc_len)

    print('done')
    time.sleep(1)

    print('Resetting counters...')
    sys.stdout.flush()
    time.sleep(1)

# Now its time to set the 10GB Interface, first we check thatis connected to the correct port.
# Then we configure the IP, MAC. PORTS 
    if not opts.skip:

        print('---------------------------')
        print('Port 0 linkup: ',)
        sys.stdout.flush()
        gbe0_link = bool(fpga.read_int('Gbe0_gbe0_linkup'))
        print(gbe0_link)
        if not gbe0_link:
            print('There is no cable plugged into port0. Please plug a cable between ports 0 and 1 to continue demo. Exiting.')

        print('---------------------------')
        print('Configuring transmitter core...',)
        sys.stdout.flush()
        gbe_tx = fpga.gbes[tx_core_name]
        gbe_tx.set_arp_table(mac_base+numpy.arange(256))
        gbe_tx.setup(mac_base+16, ip_base+16, fabric_port)
        fpga.write(tx_core_name, gbe_tx.mac.packed(), mac_location)
        fpga.write(tx_core_name, gbe_tx.ip_address.packed(), ip_location)
        value = (fpga.read_int(tx_core_name, word_offset=port_location)
                 & 0xffff0000) | (gbe_tx.port & 0xffff)
        fpga.write_int(tx_core_name, value, word_offset=port_location//4)
        gbe_tx.fabric_enable()
        print('done')

        print('Setting-up destination addresses...',)
        sys.stdout.flush()
        fpga.write_int('Gbe0_dest_ip', ip_base)
        fpga.write_int('Gbe0_dest_port', fabric_port)
        print('done')

        time.sleep(1)

# Some resets to be sure...
    fpga.write_int('man_rst', 1)
    time.sleep(.1)
    fpga.write_int('man_rst', 0)
    time.sleep(.1)
    sys.stdout.flush()
# At this point the data should be flowing thru the 10GB port

    print('done')

# set up the figure with a subplot to be plotted, the data for thisplots comefrom the BRAMS, same as the tutorials.
    fig1 = matplotlib.pyplot.figure()
    ax1 = fig1.add_subplot(1, 1, 1)
    # start the process
    fig1.canvas.manager.window.after(100, plot_stokes)
    matplotlib.pyplot.show()
    print('Plot started.')

except KeyboardInterrupt:
    exit()

exit()
