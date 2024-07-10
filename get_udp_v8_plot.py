#!/usr/bin/env python2.7.18
'''
This code demonstrates the readout of UDP packets from a SNAP spectrometer with four inputs and 256 channels each (fir+fft pts), using BRAMs and the 10GB interface. 
You need a SNAP with:
The modelsim slx model and code is modifieded from the original SNAP CASPER spectrometer and 10G tutorials.
-- A 10 MHz, 8dBm reference going into the SYNTH_OSC SMA (3rd SMA from the left) and a 10G SFP+ cable with a PC adapter.
-- A test tone, noise source (or a radio telescope signal if available) going into the ADC0 to ADC3 inputs.
casperfpga                         0.1.2
Modelsim compiled with m2021a branch
Vivado/2021.1
matlab 2021a

This code specifics, gets data from the 10G eth IF arriving at UDP (from the four ADC and 256 fir/fft channels), decodes, and plots its data. 
'''


import fcntl 
import socket 
import casperfpga,casperfpga.snapadc,time,numpy,struct,sys,logging,pylab,matplotlib
from datetime import datetime 
import struct

plot = 1

IF = "192.168.1.41" # IP from the SNAP IF

# Create a datagram socket
s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
# Bind to address and ip
localIP     = "192.168.1.25" #PC NET IF
localPort   = 10000 # Port same as SNAP
s.settimeout(5)
s.bind((localIP, localPort))
snap = "192.168.1.104" # snap raspberry PI IP
freq_range_mhz = numpy.linspace(0., 250., 256)

def swap32(x):
    return ((((x) << 8 ) & 0xFF000000) |
            (((x) >> 8 ) & 0x00FF0000) |
            (((x) << 8) & 0x0000FF00) |
            (((x) >> 8) & 0x000000FF))

def plot_data():
	matplotlib.pyplot.clf()
        acc_n = fpga.read_uint('acc_cnt')
	msg,addr = s.recvfrom(8192)
	now = datetime.now()
    	dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    	print("reading at =", dt_string) 

	while (len(msg)!=8192) and (str(addr[0]) != IF):
                acc_n = fpga.read_uint('acc_cnt')
		msg,addr = s.recvfrom(8192)
		print 'waiting ' + str(addr[0])
                time.sleep(0.2)

	if (len(msg)==8192) and (str(addr[0]) == IF): # check if the data has the correct size and from the correct IP...

        	print len(msg)
	        print addr[0]
		print fpga.read_uint('acc_cnt')
		data=struct.unpack('<1024Q',msg)
		print 'data ' + str(len(data))
		d1=[]
		d2=[]
		d3=[]
		d4=[]

		for i in range(0,256*2,2):
                    d1.append(swap32(data[i+1] >> 32 ) % 2**32)
                    d4.append(swap32(data[i+1] & 0xffffffff ) % 2**32)
                    d3.append(swap32(data[i+0] >> 32 ) % 2**32)
                    d2.append(swap32(data[i+0] & 0xffffffff ) % 2**32)


		matplotlib.pylab.plot(freq_range_mhz,10*numpy.log10(d1),label='d1')
		matplotlib.pylab.plot(freq_range_mhz,10*numpy.log10(d2),label='d2')
		matplotlib.pylab.plot(freq_range_mhz,10*numpy.log10(d3),label='d3')
		matplotlib.pylab.plot(freq_range_mhz,10*numpy.log10(d4),label='d4')

		matplotlib.pylab.title('Integration number %i.'%acc_n)
		matplotlib.pylab.ylabel('Power (dB)')
		matplotlib.pylab.grid()
		matplotlib.pylab.xlabel('Freq (MHz)')
	    	matplotlib.pylab.ylim(0, 100)
    		matplotlib.pylab.xlim(freq_range_mhz[0], freq_range_mhz[-1])

		matplotlib.pylab.legend(loc='lower right')
		fig1.canvas.draw()
		fig1.canvas.manager.window.after(100, plot_data)

#START OF MAIN:

if __name__ == '__main__':
	from optparse import OptionParser
try:
        print '***Starting 10GBe Rxing'
        condition = True
        while condition:
                try:
                    msg,addr = s.recvfrom(8192)
                except socket.timeout:
                    print 'caught a timeout'
                    break
                if (len(msg)==8192) and (str(addr[0]) == IF):  # check if the data has the correct size and from the correct IP...
                        now = datetime.now()
                        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
                        print("Starting Rxing =", dt_string) 
		        if plot:

			        print('Connecting to server ... ')
			        fpga = casperfpga.CasperFpga(snap)
			        time.sleep(1)

			        if fpga.is_connected(): # check if the board responds ok, not really needed.
			                print 'ok\n'
			                print 'Estimating FPGA clock:'
			                clock=fpga.estimate_fpga_clock()
			                print str(clock) + '[MHz]'
			                time.sleep(1)
			                clock=fpga.estimate_fpga_clock()
			                print str(clock) + '[MHz]'

			        else:
			                print 'ERROR connecting to server %s.\n'
			                quit()


		                fig1 = matplotlib.pyplot.figure()
		                ax1 = fig1.add_subplot(1,1,1)
		            # start the process
				first = 0
		                fig1.canvas.manager.window.after(100, plot_data())
		                matplotlib.pyplot.show()
		                print 'Plot started 2.'
				exit()


        print("Not getting data.") 
        exit()


except KeyboardInterrupt:
	exit()


exit()
