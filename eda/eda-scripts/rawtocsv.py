# MIT license
# Converts all Ngspice binary .raw files in ~/.xschem/simulations to .csv
# No Tkinter or GUI required
# Compatible with NumPy 2.x

from __future__ import division
import os
import numpy as np

BSIZE_SP = 512  # Max size of a line of data
MDATA_LIST = [b'title', b'date', b'plotname', b'flags', b'no. variables',
              b'no. points', b'dimensions', b'command', b'option']

def rawread(fname: str):
    """Read Ngspice binary .raw file. Returns tuple (arrays, plots)"""
    with open(fname, 'rb') as fp:
        arrs = []
        plots = []
        plot = {}
        while True:
            line = fp.readline(BSIZE_SP)
            if not line:
                break
            mdata = line.split(b':', maxsplit=1)
            if len(mdata) == 2:
                key = mdata[0].lower()
                val = mdata[1].strip()
                if key in MDATA_LIST:
                    plot[key] = val
                if key == b'variables':
                    nvars = int(plot[b'no. variables'])
                    npoints = int(plot[b'no. points'])
                    plot['varnames'] = []
                    plot['varunits'] = []
                    for varn in range(nvars):
                        varspec = fp.readline(BSIZE_SP).strip().decode('ascii').split()
                        assert(varn == int(varspec[0]))
                        plot['varnames'].append(varspec[1])
                        plot['varunits'].append(varspec[2])
                if key == b'binary':
                    rowdtype = np.dtype({
                        'names': plot['varnames'],
                        'formats': [np.complex128 if b'complex' in plot[b'flags'] else np.float64]*len(plot['varnames'])
                    })
                    arrs.append(np.fromfile(fp, dtype=rowdtype, count=int(plot[b'no. points'])))
                    plots.append(plot)
                    plot = {}
                    fp.readline()
    return arrs, plots

def convert_raw_to_csv(sim_dir):
    """Convert all .raw files in sim_dir to CSV files"""
    sim_dir = os.path.expanduser(sim_dir)
    if not os.path.exists(sim_dir):
        print(f"Simulation directory {sim_dir} does not exist.")
        return

    raw_files = [f for f in os.listdir(sim_dir) if f.endswith(".raw")]
    if not raw_files:
        print(f"No .raw files found in {sim_dir}.")
        return

    for filename in raw_files:
        raw_path = os.path.join(sim_dir, filename)
        csv_filename = filename.replace(".raw", ".csv")
        csv_path = os.path.join(sim_dir, csv_filename)
        try:
            arrs, plots = rawread(raw_path)
            # Use first plot only
            data_array = arrs[0]
            headers = data_array.dtype.names
            # Flatten structured array to 2D float array
            np.savetxt(csv_path, data_array.view(np.float64).reshape(data_array.shape + (-1,)),
                       delimiter=",", header=",".join(headers), comments='')
            print(f"Converted {filename} -> {csv_filename}")
        except Exception as e:
            print(f"Error converting {filename}: {e}")

if __name__ == '__main__':
    # Default Xschem simulations folder
    xschem_sim_dir = "~/.xschem/simulations"
    convert_raw_to_csv(xschem_sim_dir)
    print("All .raw files in the simulations folder have been processed.")
