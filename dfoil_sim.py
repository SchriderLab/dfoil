#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DFOIL: Directional introgression testing a five-taxon phylogeny
dfoil_sim - simulation of sequences for testing dfoil
James B. Pease
http://www.github.com/jbpease/dfoil
"""

from __future__ import print_function, unicode_literals
import sys
import os
import argparse
import subprocess
from random import sample

_LICENSE = """
If you use this software please cite:
Pease JB and MW Hahn. 2015.
"Detection and Polarization of Introgression in a Five-taxon Phylogeny"
Systematic Biology. 64 (4): 651-662.
http://www.dx.doi.org/10.1093/sysbio/syv023

This file is part of DFOIL.

DFOIL is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

DFOIL is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with DFOIL.  If not, see <http://www.gnu.org/licenses/>.
"""

PATTERN_CONVERT = {
    2: (6, 10, 18),
    4: (6, 12, 20),
    6: (14, 20),
    8: (10, 12, 24),
    10: (14, 26),
    12: (14, 28),
    14: (30),
    16: (18, 20, 24),
    18: (22, 26),
    20: (22, 28),
    22: (30),
    24: (26, 28),
    26: (30),
    28: (30),
    }


def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


def run_ms(params):
    """Runs the ms program to simulate sequence evolutions
        Arguments:
            params: dict from main args
    """
    nspec = 5
    nloci = params['nloci']
    coaltimes = params['coaltimes']
    theta = 4 * params['mu'] * params['popsize']
    if not params['quiet']:
        print("theta={}".format(theta))
    theta = theta * params['window']
    cmd = [params['mspath'], str(nspec), str(nloci),
           "-t", str(theta), "-I", str(nspec)] + ['1'] * nspec
    if params['recomb'] or params['rho']:
        if params['recomb']:
            rho = 4 * params['popsize'] * params['recomb'] * params['window']
        elif params['rho']:
            rho = params['window'] * params['rho']
        cmd.extend(["-r", str(rho), str(params['window'])])
        if not params['quiet']:
            print("rho={}".format(rho))
    cmd.extend(['-ej', str(coaltimes[2]), '2', '1'])
    cmd.extend(['-ej', str(coaltimes[3]), '4', '3'])
    cmd.extend(['-ej', str(coaltimes[1]), '3', '1'])
    cmd.extend(['-ej', str(coaltimes[0]), '5', '1'])
    if params['msource']:
        migration = params['mrate'] * 4 * params['popsize']
        cmd.extend(["-em", str(params['mtime_newer']), str(params['mdest']),
                    str(params['msource']), str(params['mrate'])])
        cmd.extend(["-eM", str(params['mtime_older']), '0'])
        if not params['quiet']:
            print("m={} {}>{} @{}-{}".format(
                migration, params['msource'], params['mdest'],
                params['mtime_newer'], params['mtime_older']))
    cmd.append("> {}.ms.tmp".format(params['outputfile']))
    cmd = ' '.join(cmd)
    if not params['quiet']:
        print(cmd)
    with open('{}.ms.log'.format(params['outputfile']), 'w') as tmpfile:
        process = subprocess.Popen(
            cmd, shell=True, stdout=tmpfile, stderr=tmpfile)
        process.communicate()
    if not params['quiet']:
        print("ms done")
    return '{}.ms.tmp'.format(params['outputfile'])


def process_msfile(filepath, window):
    """Process a pre-computed ms output file
        Arguments:
            filepath: path of the msfile
            window: window length
    """
    aligns = []
    seqs = []
    pos = []
    with open(filepath, 'r') as tmpfile:
        tmpfile.readline()
        tmpfile.readline()
        for line in tmpfile:
            if '//' in line:
                if seqs:
                    aligns.append(dict([(pos[j], ''.join([
                        seqs[x][j] for x in range(len(seqs))]))
                                        for j in range(len(pos))]))
                seqs = []
            elif not line.strip():
                continue
            elif line[0] == 'p':
                pos = [int(float(x) * window)
                       for x in line.rstrip().split()[1:]]
            elif line[0] in 'sm':
                continue
            else:
                seqs.append(line.rstrip())
    if seqs:
        aligns.append(dict([(pos[j], ''.join([seqs[x][j]
                                              for x in range(len(seqs))]))
                            for j in range(len(pos))]))
    return aligns


def process_aligns(aligns, params):
    """Process alignments derived from an ms output file
        Arguments:
            aligns: list of alignment allele strings
            params: dict pass-through from main args
    """
    if params['nconverge']:
        conv_sites = []
    with open(params['outputfile'], 'ab') as outfile:
        coord_start = 0
        for i, align in enumerate(aligns):
            site_counts = {0: 0}
            for (_, sitepattern) in iter(align.items()):
                pattern = int(''.join([str(int(x != sitepattern[-1]))
                                       for x in sitepattern]), 2)
                site_counts[pattern] = site_counts.get(pattern, 0) + 1
                if params['nconverge']:
                    if 0 < pattern < 30:
                        conv_sites.append(pattern)
            site_counts[0] = params['window'] - sum(site_counts.values())
            if params['nconverge']:
                conv_sites = sample(conv_sites, params['nconverge'])
                for oldp in conv_sites:
                    site_counts[oldp] -= 1
                    newp = sample(PATTERN_CONVERT[oldp], 1)
                    site_counts[newp] = site_counts.get(newp, 0) + 1
            outfile.write(('\t'.join([
                str(x) for x in ["SIM{}".format(i), coord_start] +
                [site_counts.get(elem, 0) for elem in range(0, 32, 2)]]) +
                          '\n').encode('utf-8'))
            coord_start += params['window']
    return ''


def generate_argparser():
    parser = argparse.ArgumentParser(
        prog="dfoil_sim.py",
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=_LICENSE)
    parser.add_argument("outputfile", type=os.path.abspath,
                        help=" output site count filename")
    parser.add_argument("--msfile", help="""use pre-computed ms output
                                             file instead of running ms.""")
    parser.add_argument("--nloci", type=int, default=100,
                        help="number of windows to simulate")
    parser.add_argument("--window", type=int, default=100000,
                        help="length (bp) of windows")
    parser.add_argument("--popsize", type=int, default=1e6,
                        help="Ne, effective population size (default=1e6)")
    parser.add_argument("--mu", type=float, default=7e-9,
                        help="""per site per generation mutation rate
                                (default=7e-9)""")
    parser.add_argument("--mrate", type=float, default=5e-4,
                        help="""per individual per generation migration
                                rate (default=5e-4)""")
    parser.add_argument("--msource", type=int,
                        help="1-based index of migration source population")
    parser.add_argument("--mdest", type=int,
                        help="1-based index of migration recipient population")
    parser.add_argument("--mtimes", type=float, nargs=2,
                        help="time bounds for the migration period")
    parser.add_argument("--coaltimes", type=float, nargs=4,
                        default=(3, 2, 1, 1),
                        help="""coalescent times in 4Ne units""")
    parser.add_argument("--recomb", type=float, default=0.,
                        help="""per site per generation recombination rate
                                (default=0)""")
    parser.add_argument("--rho", type=float,
                        help="""specific rho = 4*Ne*mu instead of using
                                --recomb""")
    parser.add_argument("--mspath", default="ms",
                        help="""path to ms executable""")
    parser.add_argument("--nconverge", type=int, default=0,
                        help="number of convergent sites per window")
    parser.add_argument("--quiet", action='store_true',
                        help='suppress screen output')
    parser.add_argument("--version", action="version", version="2017-06-14",
                        help="display version information and quit")
    return parser


def main(arguments=None):
    """Main method"""
    arguments = arguments if arguments is not None else sys.argv[1:]
    parser = generate_argparser()
    args = parser.parse_args(args=arguments)
    if args.rho and args.recomb:
        raise RuntimeError("Cannot use both --rho and --recomb")
    if args.mtimes:
        args.mtime_older = min(args.mtimes)
        args.mtime_newer = max(args.mtimes)
    if not args.msfile:
        if which(args.mspath) is None:
            raise RuntimeError("Cannot find 'ms' at path='{}', "
                               "is it installed?".format(
                                    args.mspath))
    # BEGIN PARAMS
    site_patterns = ['AAAAA', 'AAABA', 'AABAA', 'AABBA',
                     'ABAAA', 'ABABA', 'ABBAA', 'ABBBA',
                     'BAAAA', 'BAABA', 'BABAA', 'BABBA',
                     'BBAAA', 'BBABA', 'BBBAA', 'BBBBA']
    with open(args.outputfile, 'wb') as outfile:
        outfile.write(('#{}\n'.format('\t'.join(arguments))).encode('utf-8'))
        outfile.write(('{}\n'.format(
            '\t'.join(["#chrom", "pos"] + site_patterns)
            )).encode('utf-8'))
    # BEGIN RUNS
    msfilepath = args.msfile and args.msfile or run_ms(vars(args))
    aligns = process_msfile(msfilepath, args.window)
    process_aligns(aligns, vars(args))
    return ''

if __name__ == "__main__":
    main()
