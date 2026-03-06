# QuIC-B-Lab-Interface
Collection of code used to interface with lab equipment in the Quantum Information and Control Group lab B at the University of Arizona.

The code in this repository is customized for use in the Quantum Information and Control Group lab at the University of Arizona. The functions are not generic but can be used as templates that can be customized for use in other applications.

# NI DAQ Utilities
The functions presented in `mfp_daq_utils.py` are intended to facilitate control of the analog quantum simulator in lab B of the Quantum Information and Control Group through National Instruments DAQ cards. The name mfp is an acronym for main front panel since these functions are used by the main graphical user interface of the analog quantum simulator.

The first functions are `mfp_one_shot_record` and `mfp_one_shot` which will trigger a single cycle of the analog quantum simulator and either record data with the analog input of the DAQ card or leave the resource of the analog input open for another program to read the data.

```python
mfp_one_shot_record(port_ai,data_ao2,data_ao1,data_do_p,rate,ports_ao2,ports_ao1,ports_do,ctr_src,ctr_in,port_trg,port_aqc,init_del,background)
```

```python
mfp_one_shot(data_ao2,data_ao1,data_do,rate,ports_ao2,ports_ao1,ports_do,ctr_src,port_trg,init_del)
```

The last function `mfp_cal_aom` takes no arguments and calibrates the voltage scale for a voltage controlled AOM driver by reading the sync output of the AOM driver with a frequency counter input of the DAQ card.


# Arbitrary Waveform Generator Utilities
The functions presented in `awg_utils.py` are intended to upload arbitrary waveforms to two older models of Tabor Electronics arbitary waveform generators which are the 8026 and WW2571A. Since these two models have poor documentation, the functions in `awg_utils.py` are the result of trial and error. The three primary functions are `uploadTE8026`, `uploadTE8026_DMA`, and `uploadWW2571A`. The rest of the functions are helper functions to prepare binary data and handle SCPI commands.

# Tabor Electronics 8026 Arbitrary Waveform Generator

The Tabor Electronics 8026 has two output channels that can be programmed independently. The first function `awg_utils.uploadTE8026` allows for a basic upload of arbitrary waveform data to each channel independently along with a peak-to-peak amplitude and a sample rate which is denoted as frequency in the code. This function uploads the waveform data using standard GPIB function calls and can be quite slow because the interface is old.

```python
uploadTE8026(
    *, waveformx: np.ndarray, waveformy: np.ndarray, ampl_ptp: float, frequency: float
) -> None
```

The 8026 allows for a different method of uploading which uses direct memory access (DMA). This alternate upload method is much faster because it bypasses the cpu of the arbitrary waveform generator and permits the user to upload directly into the memory of the 8026. The speed gain using DMA is largest when uploading long waveforms. For short waveforms, in order for there to be an advantage to using DMA, multiple waveforms can be uploaded together and the memory of the 8026 can be segmented after. If the memory is segmented, then one can switch waveforms with `awg_utils.selectWaveform(segment)` where `segment` is a 1-indexed integer labeling the waveform in the sequence. The second function `awg_utils.uploadTE8026_DMA` implements the upload using DMA. This function takes two concatenated waveforms as inputs along with the peak-to-peak amplitude, sample rate, and a list of integers denoting the sizes of the individual waveforms that are concatenated in each waveform. The code does not allow the sizes of the waveforms in each channel to be set independently.

```python
uploadTE8026_DMA(
    *,
    waveformx: numpy.ndarray,
    waveformy: numpy.ndarray,
    ampl_ptp: float,
    frequency: float,
    sizes: Union[List[int], None] = None,
) -> None
```


# Tabor Electronics WW2571A

The Tabor Electronics WW2571A has an 3D arbitrary waveform feature that allows the user to modulate the amplitude, frequency, and phase of an arbitrary waveform independently at a given sample rate. the function `awg_utils.uploadWW2571A` function implements the upload procedure for the 3D waveform mode. The wavform argument of the function is a numpy.ndarray with shape (3,N) where the first row represents the amplitude in Volts, the second row represents the frequency in Hertz, and the third row represents the phase in degrees.

```python
uploadWW2571A(
    *, waveform: numpy.ndarray, max_amp: float, sample_rate: float = 1e6, offset: float = 0
) -> None
```