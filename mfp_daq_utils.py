import sys

import numpy as np
from scipy.io import loadmat

import nidaqmx as daq


def mfp_one_shot_record(port_ai,data_ao2,data_ao1,data_do_p,rate,ports_ao2,ports_ao1,ports_do,ctr_src,ctr_in,port_trg,port_aqc,init_del,background):
    ctr_src = '/'+ctr_src
    ctr_in = '/'+ctr_in
    port_trg = '/'+port_trg
    port_aqc = '/'+port_aqc
    ports_do = '/'+ports_do
    ports_ao1 = '/'+ports_ao1
    ports_ao2 = '/'+ports_ao2
    port_ai = '/'+port_ai

    data_do = data_do_p.copy()

    if background:
        # this will turn off MOT coils for background measurement
        data_do[:2,:] = 1 # turn off MOT for entire experiment
        # data_do[:2,-1] = 0 # set last point to on so that MOT coil stays on between shots


    data_do = data_do.astype(bool) # type conversion for function
    nsamps = data_ao2.shape[1] # (n_chan,n_samp)


    task1 = daq.task.Task('counter1') # counter synchronization
    co1 = task1.co_channels.add_co_pulse_chan_freq( ctr_src,units=daq.constants.FrequencyUnits.HZ,
                                                    idle_state=daq.constants.Level.LOW,initial_delay=init_del,
                                                    freq=rate,duty_cycle=.5)
    task1.timing.cfg_implicit_timing(sample_mode=daq.constants.AcquisitionType.CONTINUOUS,samps_per_chan=nsamps) # watch here
    task1.triggers.start_trigger.cfg_dig_edge_start_trig(port_trg,trigger_edge=daq.constants.Edge.RISING)


    task2 = daq.task.Task('digital out') # digital output
    task2.do_channels.add_do_chan(ports_do,line_grouping=daq.constants.LineGrouping.CHAN_PER_LINE)
    task2.timing.cfg_samp_clk_timing(rate=rate,source=ctr_src+'InternalOutput',active_edge=daq.constants.Edge.RISING,
                                     sample_mode=daq.constants.AcquisitionType.FINITE,samps_per_chan=nsamps)
    task2.write(data_do,auto_start=False,timeout=10)

    task3 = daq.task.Task('analog dev1') # analog dev1 output
    ao = task3.ao_channels.add_ao_voltage_chan(ports_ao1,min_val=-10,max_val=10,units=daq.constants.VoltageUnits.VOLTS)
    task3.timing.cfg_samp_clk_timing(rate=rate,source=ctr_src+'InternalOutput',active_edge=daq.constants.Edge.RISING,
                                     sample_mode=daq.constants.AcquisitionType.FINITE,samps_per_chan=nsamps)
    task3.write(data_ao1,auto_start=False,timeout=10)

    task4 = daq.task.Task('analog dev2') # analog dev2 output
    ao = task4.ao_channels.add_ao_voltage_chan(ports_ao2,min_val=-10,max_val=10,units=daq.constants.VoltageUnits.VOLTS)
    task4.timing.cfg_samp_clk_timing(rate=rate,source=ctr_src+'InternalOutput',active_edge=daq.constants.Edge.RISING,
                                     sample_mode=daq.constants.AcquisitionType.FINITE,samps_per_chan=nsamps)
    task4.write(data_ao2,auto_start=False,timeout=10)

    task5 = daq.task.Task('counter2') # counter for timing read
    co2 = task5.co_channels.add_co_pulse_chan_freq( ctr_in,units=daq.constants.FrequencyUnits.HZ,
                                                    idle_state=daq.constants.Level.LOW,initial_delay=.121,
                                                    freq=1e6,duty_cycle=.5)
    task5.timing.cfg_implicit_timing(sample_mode=daq.constants.AcquisitionType.CONTINUOUS,samps_per_chan=1000) # watch here
    task5.triggers.start_trigger.cfg_dig_edge_start_trig(port_aqc,trigger_edge=daq.constants.Edge.RISING)

    read_samps = 100000
    task6 = daq.task.Task('analog in') # ai channel for reading data
    ai = task6.ai_channels.add_ai_voltage_chan(port_ai,min_val=-5,max_val=5,units=daq.constants.VoltageUnits.VOLTS,)
    task6.timing.cfg_samp_clk_timing(rate=1e6,source=ctr_in+'InternalOutput',active_edge=daq.constants.Edge.RISING,
                                     sample_mode=daq.constants.AcquisitionType.FINITE,samps_per_chan=read_samps)


    task5.start()
    task4.start()
    task6.start()
    task2.start()
    task3.start()
    task1.start()

    data = np.array(task6.read(read_samps))

    task4.wait_until_done()
    task4.stop()
    task2.wait_until_done()
    task3.stop()
    task2.stop()
    task1.stop()
    task5.stop()
    task6.stop()

    task1.close()
    task2.close()
    task3.close()
    task4.close()
    task5.close()
    task6.close()

    return data # from matlab call double(ret_val) to get data as matlab array

def mfp_one_shot(data_ao2,data_ao1,data_do,rate,ports_ao2,ports_ao1,ports_do,ctr_src,port_trg,init_del):

    ctr_src = '/'+ctr_src
    port_trg = '/'+port_trg
    ports_do = '/'+ports_do
    ports_ao1 = '/'+ports_ao1
    ports_ao2 = '/'+ports_ao2


    data_do = data_do.astype(bool) # type conversion for function
    nsamps = data_ao2.shape[1] # (n_chan,n_samp)


    task1 = daq.task.Task() # counter synchronization
    co1 = task1.co_channels.add_co_pulse_chan_freq( ctr_src,units=daq.constants.FrequencyUnits.HZ,
                                                    idle_state=daq.constants.Level.LOW,initial_delay=init_del,
                                                    freq=rate,duty_cycle=.5)
    task1.timing.cfg_implicit_timing(sample_mode=daq.constants.AcquisitionType.CONTINUOUS,samps_per_chan=nsamps) # watch here
    task1.triggers.start_trigger.cfg_dig_edge_start_trig(port_trg,trigger_edge=daq.constants.Edge.RISING)


    task2 = daq.task.Task() # digital output
    task2.do_channels.add_do_chan(ports_do,line_grouping=daq.constants.LineGrouping.CHAN_PER_LINE)
    task2.timing.cfg_samp_clk_timing(rate=rate,source=ctr_src+'InternalOutput',active_edge=daq.constants.Edge.RISING,
                                     sample_mode=daq.constants.AcquisitionType.FINITE,samps_per_chan=nsamps)
    task2.write(data_do,auto_start=False,timeout=10)

    task3 = daq.task.Task() # analog dev1 output
    ao = task3.ao_channels.add_ao_voltage_chan(ports_ao1,min_val=-10,max_val=10,units=daq.constants.VoltageUnits.VOLTS)
    task3.timing.cfg_samp_clk_timing(rate=rate,source=ctr_src+'InternalOutput',active_edge=daq.constants.Edge.RISING,
                                     sample_mode=daq.constants.AcquisitionType.FINITE,samps_per_chan=nsamps)
    task3.write(data_ao1,auto_start=False,timeout=10)

    task4 = daq.task.Task() # analog dev2 output
    ao = task4.ao_channels.add_ao_voltage_chan(ports_ao2,min_val=-10,max_val=10,units=daq.constants.VoltageUnits.VOLTS)
    task4.timing.cfg_samp_clk_timing(rate=rate,source=ctr_src+'InternalOutput',active_edge=daq.constants.Edge.RISING,
                                     sample_mode=daq.constants.AcquisitionType.FINITE,samps_per_chan=nsamps)
    task4.write(data_ao2,auto_start=False,timeout=10)

    task4.start()
    task2.start()
    task3.start()
    task1.start()

    task4.wait_until_done()
    task4.stop()
    task2.wait_until_done()
    task3.stop()
    task2.stop()
    task1.stop()

    task1.close()
    task2.close()
    task3.close()
    task4.close()


## This measures m and b parameters
def mfp_aom_freq(aom):

    task1 = daq.task.Task() # measuring frequency
    task1.ci_channels.add_ci_freq_chan('/Dev2/ctr0',min_val=2,max_val=100,units=daq.constants.FrequencyUnits.HZ,
                                        edge=daq.constants.Edge.RISING,meas_method=daq.constants.CounterFrequencyMethod.HIGH_FREQUENCY_2_COUNTERS,
                                        meas_time=.1,divisor=4)

    task1.timing.cfg_implicit_timing(sample_mode=daq.constants.AcquisitionType.FINITE,samps_per_chan=3)



    task2 = daq.task.Task() # digital output
    task2.do_channels.add_do_chan('/Dev1/port0/line0:1',line_grouping=daq.constants.LineGrouping.CHAN_PER_LINE)
    task2.start()

    data = np.zeros((2,1),dtype=bool)
    if aom == 'Green':
        data[0] = False
        data[1] = False
    elif aom == 'Red':
        data[0] = True
        data[1] = False
    elif aom == 'Blue':
        data[0] = False
        data[1] = True
    elif aom == 'White':
        data[0] = True
        data[1] = True
    task2.write(data,auto_start=True,timeout=10)


    task1.start()

    x = task1.read(number_of_samples_per_channel=3)

    task2.stop()
    task1.stop()
    task2.close()
    task1.close()

    return x[1]*64/1e6


## This measures m and b parameters
# TODO expose the counter strings to the front panel
def _mfp_aom_freq_val(aom,val): # this only works with green
    task1 = daq.task.Task() # measuring frequency
    task1.ci_channels.add_ci_freq_chan('/Dev2/ctr0',min_val=2,max_val=100,units=daq.constants.FrequencyUnits.HZ,
                                        edge=daq.constants.Edge.RISING,meas_method=daq.constants.CounterFrequencyMethod.HIGH_FREQUENCY_2_COUNTERS,
                                        meas_time=.1,divisor=4)

    task1.timing.cfg_implicit_timing(sample_mode=daq.constants.AcquisitionType.FINITE,samps_per_chan=3)


    task3 = daq.task.Task() # analog dev1 output
    ao = task3.ao_channels.add_ao_voltage_chan('/Dev2/ao0',min_val=-10,max_val=10,units=daq.constants.VoltageUnits.VOLTS)
    task3.start()
    task3.write(val,auto_start=True,timeout=10)


    task2 = daq.task.Task() # digital output
    task2.do_channels.add_do_chan('/Dev1/port0/line0:1',line_grouping=daq.constants.LineGrouping.CHAN_PER_LINE)
    task2.start()

    data = np.zeros((2,1),dtype=bool)
    if aom == 'Green':
        data[0] = False
        data[1] = False
    else:
        raise ValueError('At this time only Green AOM can be measured this way')

    task2.write(data,auto_start=True,timeout=10)

    task1.start()

    x = task1.read(number_of_samples_per_channel=3)

    task3.stop()
    task2.stop()
    task1.stop()
    task3.close()
    task2.close()
    task1.close()

    return x[1]*64/1e6


def mfp_cal_aom():
    # return m and b parameters
    f1 = _mfp_aom_freq_val('Green',-.5)
    f2 = _mfp_aom_freq_val('Green',1.5)

    m = 2/(f2-f1)
    b = 1.5 - m*f2
    return np.array([m,b])

# frequency = x[1]*64/1e6 # in MHz
