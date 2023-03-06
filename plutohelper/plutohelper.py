import ast
from pathlib import Path
from types import SimpleNamespace
import re

import numpy as np

def ev(value):
    "parse a string value as python number/list or keeps it as string."
    try:
        res = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        res = value
    return res

def parse_ini(fname, i=0):
    """parses the a `pluto.ini` file and returns a namespace with the settings.
    If `fname` is a list of strings, it will be used instead of reading a file
    """
    if isinstance(fname, (Path, str)):
        text = Path(fname).read_text().split('\n')
    elif isinstance(fname, list):
        text = fname
    else:
        raise ValueError('fname needs to be a file path or list of line-strings!')

    data = SimpleNamespace()
    while i < len(text):
        line = text[i].strip()
        i += 1
        if line == '':
            continue
        if line.startswith('['):
            section_name = line.strip('[]').replace('.', '_').replace('-', '_').replace(' ', '_')
            section = SimpleNamespace()
            setattr(data, section_name, section)
        else:
            name = line.split()[0].replace('.', '_').replace('-', '_')
            string = line[len(name):].strip()

            # convert to value(s)
            ls = re.sub('\s+', ' ', string).split(' ')
            res = [ev(l) for l in ls]
            if len(res) == 1:
                res = res[0]
            
            setattr(section, name, res)
    return data

def parse_units(fname):
    """parses the code units from a pluto output log file or from and array of strings
    and returns them in a namespace
    """
    if isinstance(fname, (Path, str)):
        text = Path(fname).read_text().split('\n')
    elif isinstance(fname, list):
        text = fname
    else:
        raise ValueError('fname needs to be a file path or list of line-strings!')
    
    data = SimpleNamespace()
    keys = ['Density', 'Pressure', 'Velocity', 'Length', 'Temperature', 'Time']
    started = False
    i = 0
    while i < len(text):
        line = text[i].strip()
        i += 1
        
        if not started:
            if 'Normalization Units' in line:
                started = True
            continue
        
        for key in keys:
            if line.startswith(f'[{key}]:'):
                setattr(data, key, float(line.split(':')[1].strip().split(' ')[0]))
                
        if 'Number of processors:' in line:
            break
    
    return data


def parse_definitions(fname):
    "parses a pluto `definitions.h` file (or list of strings), returns contents as namespace"
    
    if isinstance(fname, (Path, str)):
        text = Path(fname).read_text().split('\n')
    elif isinstance(fname, list):
        text = fname
    else:
        raise ValueError('fname needs to be a file path or list of line-strings!')
    
    data = SimpleNamespace()
    for line in text:
        line = line.strip()
        
        if not line.startswith('#define'):
            continue
        
        key, value = line.split()[1:3]
        setattr(data, key, ev(value))
                
    return data

def parse_plutolog(fname):
    """parse a pluto log file for settings and definitions"""
    
    text = Path(fname).read_text().split('\n')
    i = 0
    ########## Parse Header ########
    while not text[i].strip().startswith('> Header configuration'):    
        i += 1
    i += 1
    header = SimpleNamespace()
    while not text[i].startswith('>'):
        line = text[i].strip()
        i_split = line.find(':')
        key = line[:i_split].strip().replace(' ', '_')
        value = ev(line[i_split+1:].strip())
        setattr(header, key, value)
        i += 1
    
    ######## parse  pluto.ini ########
    while not text[i].strip().startswith('+'):
        i += 1
    # found start
    i +=1
    subtext = []
    while not text[i].strip().startswith('+'):
        subtext += [text[i].strip()[1:]]
        i += 1

    config = parse_ini(subtext)
    
    ######## parse  units ########
    while not ('Normalization Units' in text[i]):
        i+= 1
    
    subtext = []
    while not ('Number of processors' in text[i]):
        subtext += [text[i]]
        i+=1
    subtext += [text[i]]
    
    units = parse_units(subtext)
    
    ##### RETURN ALL ######
    data = SimpleNamespace()
    setattr(data, 'header', header)
    setattr(data, 'ini', config)
    setattr(data, 'units', units)
    return data


def make_grids(d, config, **kwargs):
    """generates various grids for plotting

    Parameters
    ----------
    d : pyPLUTO.pload.pload
        pluto data read in with pyPLUTO
    config : SimpleNamespace | None
        reads dimensions and geometry from this configuration
        if this is none, then `geometry` and `dimensions` need
        to be given as keywords.

    Returns
    -------
    SimpleNamespace
        this contains various grids to help with analysis/plotting:
        `R`, `Ri`: cylindrical radius of center and interface (1D)
        `r`, `ri`: spherical radius of center and interface (1D) in spherical geom.
        `rr`, `rri`, `th`, `thi`: 2D spherical radius and theta array in polar geom.
        `z`, `zi`: polar height above the mid plane, 1D, in polar geom.
        `zz`, `zzi`: polar height $z$ above the mid plane, 2D, in spherical geom.
        `RR`, `RRi`: cylindrical radius, 2D, in spherical geom.
        `xx`, `xxi`, `yy`, `yyi`: x and y position 2D arrays in mid-plane
    """
    g = SimpleNamespace()

    if config is None:
        geometry = kwargs.get('geometry')
        dimensions = kwargs.get('dimensions')
    else:
        geometry = config.header.GEOMETRY.lower()
        dimensions = config.header.DIMENSIONS

    if geometry == 'polar':
        g.R  = d.x1
        g.Ri = d.x1r
        if dimensions == 2:
            g.z  = 0.0
            g.r  = g.R
            g.ri = g.Ri
            g.th = 0.5 * np.pi
        else:
            g.z  = d.x3
            g.zi = d.x3r
            g.rr  = np.sqrt((g.R * g.R)[:, None] + (g.z * g.z)[None, :])
            g.rri  = np.sqrt((g.Ri * g.Ri)[:, None] + (g.zi * g.zi)[None, :])
            g.thth = np.arctan2(g.R[:, None], g.z[None, :])

        g.xx  = g.R[:, None] * np.cos(d.x2[None, :])
        g.yy  = g.R[:, None] * np.sin(d.x2[None, :])

    elif geometry == 'spherical':
            g.r  = d.x1
            g.ri = d.x1r
            g.th = d.x2
            g.thi = d.x2r
            g.phi = d.x3
            g.phii = d.x3r
            
            g.RR = g.r[:, None] * np.sin(g.th[None, :])
            g.zz = g.r[:, None] * np.cos(g.th[None, :])
            
            g.RRi = g.ri[:, None] * np.sin(g.thi[None, :])
            g.zzi = g.ri[:, None] * np.cos(g.thi[None, :])
            
            g.xx = g.r[:, None] * np.cos(g.phi[None, :])
            g.yy = g.r[:, None] * np.sin(g.phi[None, :])
            
            g.xxi = g.ri[:, None] * np.cos(g.phii[None, :])
            g.yyi = g.ri[:, None] * np.sin(g.phii[None, :])
            #x = r*sin(th)*cos(x3);
            #y = r*sin(th)*sin(x3);
    return g


def compute_vorticity(g, d, config, i_mid=None, deltai=0, normalize=True):
    """computes vorticity for the given snapshot.
    Uses
    config.header.ROTATION = 'YES' | 'NO'
    

    Parameters
    ----------
    g : grid
        Simple namespace with grid attributes
    d : data
        data name space
    config : SimpleNamespace
        cofiguration as read from pluto.log
    i_mid : int, optional
        which index in theta to plot, by default None
    deltai : int, optional
        how many cells around `i_mid` to average, by default 0
    normalize : bool, optional
        normalize by Keplerian vorticity, by default True

    Returns
    -------
    ndarray
        vorticity in z, possibly normalized by Keplerian
    """
    
    if config.header.GEOMETRY.lower() != 'spherical':
        raise ValueError('vorticity computation only implemented for 3D spherical only')
        
    if i_mid is None:
        i_mid = d.rho.shape[1] // 2

    # if mid plane is not a cell, we average the cells above and below the mid plane
    if deltai==0 and (i_mid < i_mid / 2):
        deltai = 1

    # dx and dy between the grid cells
    dr = g.r[2:] - g.r[:-2]
    dphi = g.phi[2:] - g.phi[:-2]

    # define frame rotation

    if config.header.ROTATION == 'YES':
        vphi_rot = g.r.copy()[:, None]
    else:
        vphi_rot = 0.0

    # radial and phi velocity, use the mid-plane values

    vr   = d.vx1[:, i_mid-deltai:i_mid + deltai + 1, :].mean(1)
    vphi = d.vx3[:, i_mid-deltai:i_mid + deltai + 1, :].mean(1) + vphi_rot

    # compute the first and second term in the brackets
    first_term = (g.r[2:, None] * vphi[2:, 1:-1] - g.r[:-2, None] * vphi[:-2, 1:-1]) / dr[:, None]
    second_term = (vr[1:-1, 2:] - vr[1:-1, :-2]) / dphi

    # add them and divide by r
    vort_z = (first_term + second_term) / g.r[1:-1, None]

    # normalize to keplerian
    if normalize:
        vort_z = vort_z / (0.5 * g.r[1:-1]**-1.5)[:, None]
        
    return vort_z