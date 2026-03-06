import os, struct, time, traceback, warnings
from itertools import chain
from typing import List, Union
import numpy as np
import pyvisa

# import matplotlib.pyplot as plt


def te8026_prepare_bytes(
    data: np.ndarray, ampl_ptp: float, dma: bool = True
) -> tuple[bytes, int]:
    # 0       is -ampl_ptp/2
    # 2**14-1 is +ampl_ptp/2

    N_data = len(data)
    n_extra = (4 - (N_data % 4)) % 4
    data = np.concatenate(
        (data, np.zeros(n_extra))
    )  # length of data must be a multiple of 4 for hardware reasons
    N_data = len(data)
    full_scale = 0x3FFF
    zero_point = 0x1FFF
    data = (data * zero_point / (ampl_ptp / 2) + zero_point).astype(
        np.uint16
    )  # map data onto integer representation
    data[data > full_scale] = full_scale  # truncate data to be a 14 bit integer
    if dma:
        data[-1] |= 0x8000  # this sets the flag to stop DMA
        buf = struct.pack(f"<{len(data):d}H", *data)
    else:
        # the manual says that it should be in little endian, but that doesn't work for whatever reason, so big endian it is
        buf = struct.pack(f">{len(data):d}H", *data)

    return buf, N_data


def te8026_setOUTP(dev: pyvisa.resources.Resource, state: bool) -> None:
    state_str = "ON" if state else "OFF"
    opc = dev.query(f"*OPC?;:INST 1;OUTP {state_str:s};:INST 2;:OUTP {state_str:s}")
    if opc != "1":
        raise RuntimeError("Operation complete bit failed")


def te8026_reset(dev: pyvisa.resources.Resource) -> None:
    opc = dev.query("*OPC?;*RST;*CLS")
    if opc != "1":
        raise RuntimeError("Operation complete bit failed")


def te8026_select_segment(dev: pyvisa.resources.Resource, segment: int) -> None:
    opc = dev.query(f"*OPC?;INST 1;:TRAC:SEL {segment:d};:INST 2;:TRAC:SEL {segment:d}")
    if opc != "1":
        raise RuntimeError("Operation complete bit failed")


# this function is obsolete and has been replaced by uploadTE8026_DMA
def uploadTE8026(
    *, waveformx: np.ndarray, waveformy: np.ndarray, ampl_ptp: float, frequency: float
) -> None:

    data_bytesx, N_data = te8026_prepare_bytes(waveformx, ampl_ptp, dma=False)
    data_bytesy, N_data = te8026_prepare_bytes(waveformy, ampl_ptp, dma=False)
    data_bytes = [data_bytesx, data_bytesy]

    N_bytes = 2 * N_data

    # data_bytes = waveform.astype(np.uint16)
    # TODO for each waveform, need to make last byte have DMA termination bit

    # *IDN? should return 'Tabor Electronics,WW2571A,0,2.0'
    # *OPT? should return 2
    rm = pyvisa.ResourceManager()
    try:
        # possibly loop through devices to find the correct address
        # at the moment, address can be retrieved from os.environ['WW2571A_ADDR']
        address = os.environ["TE8026_ADDR"]
        dev = rm.open_resource(address)

        dev.baud_rate = 115200
        dev.write_termination = "\n"
        dev.read_termination = "\n"

        dev.write(
            "*CLS"
        )  # clears any errors in principle # I don't think this does what it sounds like it does
        dev.write("*RST")

        idn = dev.query("*IDN?")
        opt = dev.query("*OPT?")

        # turn both outputs off
        for instr in [1, 2]:
            # setOUTP(dev,instr+1,'0')
            dev.write(f"INST {instr:d}")
            time.sleep(0.1)
            dev.write("OUTP OFF")
            time.sleep(0.1)

        for instr in [0, 1]:
            dev.write(f"INST {instr+1:d}")

            # configure trigger

            dev.write(":INIT:CONT OFF")
            dev.write(":TRIG:GATE OFF")

            dev.write(":TRIG:BURS ON")
            dev.write(":TRIG:COUNT 1")
            dev.write(":TRIG:SLOP POS")
            dev.write(":TRIG:SOUR:ADV EXT")
            # err = dev.query(':SYST:ERR?')
            # print(err)

            # upload
            dev.write(":FUNC:MODE USER")
            dev.write(f":VOLT {ampl_ptp:e}")
            dev.write(f":FREQ:RAST {frequency:e}")
            dev.write(f":TRAC:DEF 1,{N_data:d}")
            err = dev.query("*OPC?")
            print(err)
            dev.write(":TRAC:SEL 1")

            # dev.write_raw('DMA ON'.encode('utf-8')) # this is a faster upload protocal
            # time.sleep(.1) # wait 100 ms for stability
            # last byte must have high bit set to 1 to terminate DMA

            header = "#" + str(len(str(N_bytes))) + str(N_bytes)
            dev.write_raw(f":TRAC:DATA {header}\n".encode("utf-8"))

            # dev.read_bytes(1)
            i = 0
            chunk_size = 1000
            while i < N_bytes:
                chunk = slice(i, min(i + chunk_size, N_bytes), None)
                dev.write_raw(data_bytes[instr][chunk])
                i += chunk_size

            time.sleep(0.1)
            err = dev.query(":SYST:ERR?")
            print(err)

        for instr in range(2):
            dev.write(f"INST {instr+1:d}")
            time.sleep(0.1)
            dev.write("OUTP ON")
            time.sleep(0.1)

    except Exception as e:
        print(
            e
        )  # I am not sure if this actually resolves errors, I think the visa library may have its own error handler
        # sys.stdout.write('\a\r')
        if isinstance(e, pyvisa.errors.VisaIOError):
            if e.error_code == pyvisa.errors.StatusCode.error_resource_not_found:
                warnings.warn("Resource not found")
            else:
                warnings.warn("Error encountered in probe waveform upload")
                dev.close()
                rm.close()
    finally:
        dev.close()
        rm.close()


def selectWaveform(segment):
    rm = pyvisa.ResourceManager()
    try:  # this won't catch VISA errors, only python and pyvisa errors
        assert segment > 0
        # possibly loop through devices to find the correct address
        # at the moment, address can be retrieved from os.environ['WW2571A_ADDR']
        address = os.environ["TE8026_ADDR"]
        dev = rm.open_resource(address)
        # dev.baud_rate = 115200
        dev.write_termination = "\n"
        dev.read_termination = "\n"

        opc = dev.query(f"*OPC?;:TRAC:SEL {segment:d}")

    except Exception as e:
        print(traceback.format_exc())
        if isinstance(e, pyvisa.errors.VisaIOError):
            if e.error_code == pyvisa.errors.StatusCode.error_resource_not_found:
                warnings.warn("Resource not found")
            else:
                warnings.warn("Error encountered in waveform segment selection")
                dev.close()
                rm.close()


def upload_segment_table(dev: pyvisa.resources.Resource, sizes: List[int]) -> None:
    opc = dev.query("*OPC?;:TRAC:DEL:ALL")

    addr = [0x100]
    for i in range(len(sizes) - 1):
        next_addr = int(addr[i] + sizes[i] / 4)
        addr.append(next_addr)

    # use bytearray because it is read-write
    table_data = bytearray(
        struct.pack(f">{2*len(sizes)}I", *chain(*zip(addr, sizes)))
    )  # documentation says little endian, but it is big endian
    del table_data[0::4]  # truncate data to 3 byte words

    N_bytes = len(table_data)
    header = "#" + str(len(str(N_bytes))) + str(N_bytes)

    # dev.write_raw(f"*OPC?;:SEGM {header}".encode("utf-8"))
    # BUG this works for 10 segments at a time, but not more
    dev.write_raw(f"SEGM {header}".encode("utf-8") + table_data + b"1\n")
    # dev.write_raw(bytes(table_data)+b'1\n')
    err = dev.query(":SYST:ERR?")
    print("segment err", err)
    opc = dev.query("*OPC?;:TRAC:SEL 1")


# need to use *OPC? before commands to insure they are completed before next call to dev.write
def uploadTE8026_DMA(
    *,
    waveformx: np.ndarray,
    waveformy: np.ndarray,
    ampl_ptp: float,
    frequency: float,
    sizes: Union[List[int], None] = None,
) -> None:

    data_bytesx, N_data = te8026_prepare_bytes(waveformx, ampl_ptp, dma=True)
    data_bytesy, N_data = te8026_prepare_bytes(waveformy, ampl_ptp, dma=True)
    data_bytes = [data_bytesx, data_bytesy]

    N_bytes = 2 * N_data

    rm = pyvisa.ResourceManager()
    try:  # this won't catch VISA errors, only python and pyvisa errors
        # possibly loop through devices to find the correct address
        # at the moment, address can be retrieved from os.environ['WW2571A_ADDR']
        address = os.environ["TE8026_ADDR"]
        dev = rm.open_resource(address)
        # dev.baud_rate = 115200
        dev.write_termination = "\n"
        dev.read_termination = "\n"

        te8026_reset(dev)

        # idn = dev.query('*IDN?') # returns 'Tabor Electronics,8026,0,2.00'
        # opt = dev.query('*OPT?') # BUG returns value of '2' which is not listed as a valid option in manual

        # turn both outputs off
        te8026_setOUTP(dev, False)

        for instr in [0, 1]:

            # configure trigger
            opc = dev.query(
                f"*OPC?;:INST {instr+1:d};:INIT:CONT OFF;:TRIG:GATE OFF;:TRIG:BURS OFF;:TRIG:SLOP POS;:TRIG:SOUR:ADV EXT"
            )
            print(opc)

            # upload
            opc = dev.query(
                f"*OPC?;:FUNC:MODE USER;:VOLT {ampl_ptp:e};:FREQ:RAST {frequency:e};:TRAC:DEF 1,{N_data:d};:TRAC:SEL 1"
            )
            print(opc)
            err = dev.query(
                "SYST:ERR?"
            )  # 0 if no error, -311 if you touch any of the code
            print(err)

            dev.write_raw(
                "DMA ON".encode("utf-8")
            )  # this is the fastest upload protocal
            time.sleep(0.1)  # manual suggests the code wait 100 ms for stability
            # last byte must have high bit set to 1 to terminate DMA

            i = 0
            chunk_size = 1000  # this value is arbitrary and can be changed
            # sending bytes in chunks, waveforms are often more than 100_000 points so this prevents a timeout
            while i < N_bytes:
                chunk = slice(i, min(i + chunk_size, N_bytes), None)
                dev.write_raw(data_bytes[instr][chunk])
                i += chunk_size

            time.sleep(0.1)
            err = dev.query(":SYST:ERR?")  # 0 if no error
            print(err)
            # test by uploading several segments and deleting them later
            # print(err)
            if sizes is not None:
                upload_segment_table(dev, sizes)
            # TODO consider adding a TRAC:DEL:ALL and then redefine all the trac segments

        te8026_setOUTP(dev, True)

    except Exception as e:
        print(traceback.format_exc())
        if isinstance(e, pyvisa.errors.VisaIOError):
            if e.error_code == pyvisa.errors.StatusCode.error_resource_not_found:
                warnings.warn("Resource not found")
            else:
                warnings.warn("Error encountered in 8026 waveform upload")
                dev.close()
                rm.close()
    finally:
        dev.close()  # does't really work
        rm.close()


# WW2571A


def ww2571A_prepare_bytes(data: np.ndarray, max_amp: float) -> tuple[bytes, int]:

    # 2**12 - 1 == 0xFFF
    # 2**30 - 1 == 0x40000000
    # 2**14 - 1 == 0x3FFF

    MAX_FREQ = 75e6
    MAX_PHASE = 360
    _, Npts = data.shape
    sync = (np.zeros(Npts, dtype=np.uint16)).view(np.uint8).reshape(-1, 2)
    amp = (
        ((data[0, :] * 0xFFF) // max_amp)
        .astype(np.uint16)
        .view(np.uint8)
        .reshape(-1, 2)
    )
    freq = (
        ((data[1, :] * 0x40000000) // MAX_FREQ)
        .astype(np.uint32)
        .view(np.uint8)
        .reshape(-1, 4)
    )
    phase = (
        ((data[2, :] * 0x3FFF) // MAX_PHASE)
        .astype(np.uint16)
        .view(np.uint8)
        .reshape(-1, 2)
    )

    # (sync,amp,freq,phase)
    return np.hstack((sync, amp, freq, phase)).flatten().tobytes(), Npts


# need to test this
def uploadWW2571A(
    *, waveform: np.ndarray, max_amp: float, sample_rate: float = 1e6, offset: float = 0
) -> None:
    # waveform shape (3,Npts)
    # vstack(amp,freq,phase)

    data_bytes, N_data = ww2571A_prepare_bytes(waveform, max_amp)
    N_bytes = 10 * N_data  # there are 10 bytes per data point

    # *IDN? should return 'Tabor Electronics,WW2571A,0,2.0'
    # *OPT? should return 2
    rm = pyvisa.ResourceManager()
    try:  # this won't catch VISA errors, only python and pyvisa errors
        # possibly loop through devices to find the correct address
        # at the moment, address can be retrieved from os.environ['WW2571A_ADDR']
        address = os.environ["WW2571A_ADDR"]
        dev = rm.open_resource(address)
        dev.baud_rate = 115200
        dev.write_termination = "\n"
        dev.read_termination = "\n"

        dev.write("*CLS")
        dev.write("*RST")

        dev.write("FUNC:MODE USER")
        dev.write("INIT:CONT OFF;:TRIG:GATE OFF;:TRIG:BURS OFF")
        dev.write("OUTP OFF")
        err = dev.query("SYST:ERR?")
        dev.write(
            f"3D:RAST {sample_rate:e};:3D:MARK 1;:FUNC:MODE MOD;:MOD:TYPE 3D;:VOLT {max_amp:f};:VOLT:OFFS  {offset:f}"
        )

        header = "#" + str(len(str(N_bytes))) + str(N_bytes)
        dev.write_raw(f":TRAC:DATA {header}\n".encode("utf-8"))
        dev.read_bytes(
            1
        )  # read OPC bit but don't read termination character else it will crash

        i = 0
        chunk_size = 1000
        while i < N_bytes:
            chunk = slice(i, min(i + chunk_size, N_bytes), None)
            dev.write_raw(data_bytes[chunk])
            i += chunk_size

        time.sleep(0.1)
        err = dev.query(":SYST:ERR?")
        print(err)

    except Exception as e:
        print(traceback.format_exc())
        if isinstance(e, pyvisa.errors.VisaIOError):
            if e.error_code == pyvisa.errors.StatusCode.error_resource_not_found:
                warnings.warn("Resource not found")
            else:
                warnings.warn("Error encountered in WW2571A waveform upload")
                dev.close()
                rm.close()
    finally:
        dev.close()  # does't really work
        rm.close()
