# Snap_10G_tut

This code demonstrates the readout of a SNAP spectrometer with four inputs and 256 channels each (fir+fft pts), using BRAMs and the 10GB interface. 
The modelsim slx model and code is modifieded from the original SNAP CASPER spectrometer and 10G tutorials.

You need a SNAP with:
-- A 10 MHz, 8dBm reference going into the SYNTH_OSC SMA (3rd SMA from the left) and a 10G SFP+ cable with a PC adapter.
-- A test tone, noise source (or a radio telescope signal if available) going into the ADC0 to ADC3 inputs.
Python 2.7(.18) -> casperfpga 0.1.2
Modelsim compiled with m2021a branch
Vivado/2021.1
matlab 2021a
