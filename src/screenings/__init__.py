#!/usr/bin/env python

# Copyright (C) <2015> EMBL-European Bioinformatics Institute

# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# Neither the institution name nor the name screenings can
# be used to endorse or promote products derived from this
# software without prior written permission. For written
# permission, please contact <marco@ebi.ac.uk>.

# Products derived from this software may not be called
# screenings nor may screenings appear in their names
# without prior written permission of the developers.
# You should have received a copy of the GNU General Public
# License along with this program. If not, see
# <http://www.gnu.org/licenses/>.

__author__ = 'Marco Galardini'
__version__ = '0.0.1'

def get_header(infile):
    '''Get the header of an Iris file'''
    return [l.strip() for (i,l) in zip(range(6), open(infile))]

def parse_iris(infile, platefile=None, platenumber=None, skiprows=6):
    '''Parse an Iris output

    Returns a Pandas dataframe.
    If a plate file is provided, a column with strain name will be added.
    '''
    import pandas as pd

    plate = pd.read_table(infile, skiprows=skiprows)

    # Add the spots identifiers
    if platefile is not None:
        plate['id'] = [x[0] for x in sorted(parse_names(platefile, plate=platenumber),
                                     key=lambda x: (x[3][1], x[3][2]))]
        # Scar-tissue code (a multi-index is more complicated)
        #plate['name'] = [x[1] for x in sorted(parse_names(platefile),
        #                             key=lambda x: (x[3][1], x[3][2]))]
        #plate['nt'] = [x[2][0] for x in sorted(parse_names(platefile),
        #                             key=lambda x: (x[3][1], x[3][2]))]
        #plate.set_index(['id', 'name', 'nt'], inplace=True)
        plate.set_index('id', inplace=True)

    return plate

def parse_names(infile, plate=None):
    '''Get the position and names for each strain
    
    Yields id, name, (p384, row, column), (p1536, row, column)
    
    For the 384 plate, a number is yielded instead of the column char
    '''
    alphabetical = 'ABCDEFGHIJKLMNOP'
    
    import csv
    with open(infile, 'rb') as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        for r in reader:
            if plate is not None and r[10] != plate:
                continue
            yield r[4], r[6], (r[7], alphabetical.index(r[9])+1, int(r[8])), (
                    r[10], int(r[11]), int(r[12]))

def fix_missing(df, size=7):
    '''Report putative areas where colonies have not been pinned

    Parameters
    ----------
    df : a DataFrame generated from Iris
         "colony size" column should be present;
         same as "row" and "column"
    size : size of the empty areas that trigger their recognition 

    Returns
    -------
    area: an iterable of (row, column) identifiers
    '''
    import networkx as nx

    # Identify connected components in the "empty spots" graph
    g = nx.Graph()

    df = df.set_index(['row', 'column'])

    for r, c in df[df['colony size'] == 0].index:
        g.add_node((r, c))
    for r, c in g.nodes():
        for r1, c1 in g.nodes():
            if r == r1 and c == c1:
                continue
            if r1 in range(r-1, r+2) and c1 in range(c-1, c+2):
                g.add_edge((r, c), (r1, c1))

    return [y for x in nx.connected_components(g)
            if len(x) > size for y in x]

def fix_circularity(df,
        circularity=0.5,
        size=1000,
        above=False):
    '''Fix an Iris dataframe for circularity issues

    Parameters
    ----------
    df : a DataFrame generated from Iris
         "colony size" and "circularity" columns should be present;
         "colony color intensity" will also be corrected, if presenti,
         same as "circularity", if present
    circularity : circularity threshold
    size : size threshold; colonies above this size won't be fixed
    above : consider colonies above the size threshold

    Returns
    -------
    df : the fixed DataFrame
    '''
    import numpy as np

    if not above:
        size_t = df['colony size'] < size
    else:
        size_t = df['colony size'] >= size

    df.ix[(df['circularity'] < circularity) &
          (size_t),
          'colony size'] = np.nan 

    try:
        df.ix[(df['circularity'] < circularity) &
                (size_t),
            'colony color intensity'] = np.nan
    except:
        pass
    
    return df

def remove_colonies(df, remove):
    '''Fix an Iris dataframe by removing colonies

    Parameters
    ----------
    df : dataframe generated from Iris
         "colony size" and "colony color intensity" columns should be present,
         as well as "circularity", "row" and "column"
    remove: an iterable of (row, column) tuples to be removed
    
    Returns
    -------
    df : the fixed DataFrame
    '''
    import numpy as np

    for r, c in remove:
        df.ix[(df['row'] == r) &
                (df['column'] == c),
                'colony size'] = np.nan
        df.ix[(df['row'] == r) &
                (df['column'] == c),
                'colony color intensity'] = np.nan
        df.ix[(df['row'] == r) &
                (df['column'] == c),
                'circularity'] = np.nan

    return df

def plate_middle_mean(df, param='colony size'):
    '''
    Calculates the Plate Middle Mean

    Mean of central colonies in the 40-60 sizes percentiles
    Takes as input a dataframe generated by Iris
    '''
    import numpy as np
    from scipy.stats.mstats import mquantiles

    data = df[(df.row > 2) &
              (df.row < 31) &
              (df.column > 2) &
              (df.column < 47)][param]

    data = np.ma.masked_array(data.as_matrix().flatten())

    Q1, Q2 = mquantiles(data,
                        prob=[0.40, 0.60])

    return data[(data >= Q1) & (data <= Q2)].mean()

def scale_iris(df, param='colony size', all_median=None):
    '''
    Scale an Iris dataframe
    
    The same approach as EMAP is applied
    '''
    pmm = plate_middle_mean(df, param=param)

    scaled = normalize_outer(df,
                             param=param,
                             pmm=True)

    if all_median is None:
        all_median = median(scaled[param])

    df[param] = (scaled[param] - all_median)/ pmm

    return df

def median(data):
    '''
    Get the median of the input data
    
    Works with columns extracted from a Pandas DataFrame
    '''
    import numpy as np

    data = np.ma.masked_array(data.as_matrix(),
                   np.isnan(data.as_matrix()))
    
    return np.ma.median(data)

def variance(data):
    '''
    Get the sample variance of the input data
    
    Works with columns extracted from a Pandas DataFrame
    '''
    import numpy as np
    
    data = np.ma.masked_array(data.as_matrix(),
                   np.isnan(data.as_matrix()))
    
    return np.ma.var(data)

def normalize_outer(df, param='colony size',
                    pmm=False):
    '''
    Bring the outer colonies to the center median
    
    Takes in input a dataframe generated from an Iris file
    if plate_middle_mean is set, the EMAP approach will be used
    '''
    if not pmm:
        inner_median = median(df[(df.row > 2) &
                                (df.row < 31) &
                                (df.column > 2) &
                                (df.column < 47)][param])
    else: 
        inner_median = plate_middle_mean(df, param=param)

    outer_median = median(df[(df.row < 3) |
                            (df.row > 30) |
                            (df.column < 3) |
                            (df.column > 46)][param])
    
    outer_size = df[(df.row < 3) |
                   (df.row > 30) |
                   (df.column < 3) |
                   (df.column > 46)][param]
    
    df.ix[(df.row < 3) |
         (df.row > 30) |
         (df.column < 3) |
         (df.column > 46), param] =  outer_size * (
                 inner_median/outer_median
                 )
    
    return df

def variance_jackknife(df,
        param='colony size',
        var_threshold=0.9):
    '''Fix an Iris dataframe by removing abnormaly variant colonies

    Parameters
    ----------
    df : dataframe generated from Iris
         the parameter on which the analysis is performed should be present,
         as well as "row", "column", "colony color intensity", "colony size"
         and "circularity"
    param : parameter used for the variance analysis
    var_threshold : remove colonies which contribute to variance over
                    this threshold
    
    Returns
    -------
    df : the fixed DataFrame
    '''
    import numpy as np
    from copy import deepcopy

    # Copy the original dataframe
    m1 = deepcopy(df)

    # First bring the outer colonies to the inner median
    m = normalize_outer(df, param)
    
    strains = {x for x in m.index}
    for strain in strains:
        # Stop if there are less than 2 non-null points
        try:
            float(m.loc[strain, param])
            continue
        except:
            pass
        try:
            m.loc[strain,
                  param].dropna()
        except:
            continue
            
        spots = len(m.loc[strain,
            param].dropna())
            
        if spots < 3:
            continue
            
        discard = set()
        
        total_variance = variance(m.loc[
            strain].dropna()[param]) * (spots - 1)
        
        for s, r, c in zip(m.loc[strain].dropna()[param].as_matrix(),
                        m.loc[strain].dropna()['row'].as_matrix(),
                        m.loc[strain].dropna()['column'].as_matrix()):
            s_variance = variance(m[(m.row != r) &
                      (m.column != c)].loc[strain,
                          param])
            s_variance = np.power(s_variance, 2) * (spots - 2)
            if (total_variance-s_variance) > (var_threshold*total_variance):
                discard.add((r, c))
        
        # If we have to discard > 2 point it is likely a false positive
        # (i.e. two values are almost exactly the same)
        # Same if we have to discard 2 points, but there may be genuine 
        # contaminations/mistakes there
        if len(discard) > 2:
            continue
        
        # NaN the input parameter,
        # colony size and color
        # in the original dataframe
        for row, column in discard:
            m1.ix[(m1.row == row) &
                  (m1.column == column), param] = np.nan
            m1.ix[(m1.row == row) &
                  (m1.column == column),
                  'colony size'] = np.nan
            m1.ix[(m1.row == row) &
                  (m1.column == column),
                  'colony color intensity'] = np.nan
            m1.ix[(m1.row == row) &
                  (m1.column == column),
                  'circularity'] = np.nan

    return m1

def emap_variance_jackknife(dfs,
        param='colony size',
        var_threshold=0.9,
        all_median=516.1):
    '''Flag which replicate contributes the most to the variance

    Parameters
    ----------
    dfs : dictionary of dataframes generated from Iris
         the parameter on which the analysis is performed should be present
    param : parameter used for the variance analysis
    var_threshold : remove colonies which contribute to variance over
                    this threshold
    all_median : Median of colony size across the whole experiment;
                 default is taken from the EMAP paper

    Returns
    -------
    fishy : list of "fishy" Iris dataframes
    '''
    import numpy as np
    import pandas as pd

    # Normalize the Data Frames
    for fname, df in dfs.items():
        dfs[fname] = scale_iris(df, param, all_median)
    
    # We assume that all Data Frames have the same indexes
    strains = {x for x in df.index}
    
    fishy = {}
    
    for strain in strains:
        var = {}
        for fname, df in dfs.items():
            v = df.loc[strain, param].dropna()
            if len(v.shape) == 0 or v.shape[0] == 0:
                continue
            elif v.shape[0] == 1:
                var[fname] = [v[0]]
            else:
                var[fname] = v.as_matrix()

        spots = len([x for y in var.values() for x in y])
            
        if spots == 1:
            continue
            
        total_variance = variance(pd.DataFrame([x for y in var.values() for x in y])) * (spots - 1)
        
        for fname in var:
            s_variance = variance(pd.DataFrame([x for (k, y) in var.items() if k != fname for x in y]))
            s_variance = np.power(s_variance, 2) * (spots - len(var[fname]))
            if (total_variance-s_variance) > (var_threshold*total_variance):
                fishy[fname] = fishy.get(fname, set())
                fishy[fname].add( strain )
    
    return fishy

def iqr(data):
    '''
    Compute the interquartile range
    
    Equivalent to R's IQR function
    Imortant: no NaN's should be present
    '''
    from scipy import stats

    Q1, Q3 = stats.mstats.mquantiles(data,
                        prob=[0.25, 0.75],
                        alphap=1,
                        betap=1)
    return Q3 - Q1

def mad(data, c=0.6745):
    '''
    Compute the MAD
    
    Equivalent to R's mad function
    Imortant: no NaN's should be present
    '''
    import numpy as np

    return np.ma.median(np.ma.fabs(data - np.ma.median(data))) / c

def iqr_norm(data):
    '''
    Normalize the data using the IQR
    (Inter-Quartile Range)
    
    Works with columns extracted from a Pandas DataFrame
    
    Equivalent to the R snippet used in the Typas lab
    (minor changes in the normalized score can be seen)
    '''
    import numpy as np
    from scipy import stats

    data = np.ma.masked_array(data.as_matrix(),
                   np.isnan(data.as_matrix()))
    
    iqr_std = stats.norm.ppf(0.75)*2
    
    return iqr_std * (data - np.median(data))/iqr(data)

def mad_norm(data):
    '''
    Normalize the data using the MAD
    (Mean Absolute Deviation)
    
    Works with columns extracted from a Pandas DataFrame
    
    Equivalent to the R snippet used in the Typas lab
    (minor changes in the normalized score can be seen)
    '''
    import numpy as np
    import math

    data = np.ma.masked_array(data.as_matrix(),
                   np.isnan(data.as_matrix()))
    
    mad_std = math.sqrt(2/math.pi)
    
    return mad_std * (data - np.ma.median(data))/mad(data)

