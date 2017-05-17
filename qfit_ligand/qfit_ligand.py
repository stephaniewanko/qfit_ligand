"""Hierarchically build a multiconformer ligand."""

import argparse
import os.path
import sys
import logging
logger = logging.getLogger(__name__)

from .builders import HierarchicalBuilder
from .structure import Ligand, Structure
from .volume import Volume
from .helpers import mkdir_p


def parse_args():

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("xmap", type=str,
            help="X-ray density map in CCP4 format with P1 symmetry.")
    p.add_argument("resolution", type=float,
            help="Map resolution in angstrom.")
    p.add_argument("ligand", type=str,
            help="Ligand file in PDB format.")
    p.add_argument("-r", "--receptor", dest="receptor", type=str, default=None,
            metavar="<file>",
            help="PDB file containing receptor for clash detection.")
    #p.add_argument("-g", "--global-search", action="store_true",
    #        help="Perform a global search.")
    p.add_argument("-nb", "--no-build", action="store_true",
            help="Do not build ligand.")
    p.add_argument("-nl", "--no-local", action="store_true",
            help="Do not perform a local search.")
    p.add_argument("-b", "--build-stepsize", type=int, default=1, metavar="<int>",
            help="Number of internal degrees that are sampled/build per iteration.")
    p.add_argument("-s", "--stepsize", type=float, default=1, metavar="<float>",
            help="Stepsize for dihedral angle sampling in degree.")
    p.add_argument("--no-scale", action="store_true",
            help="Do not scale density while building ligand.")
    p.add_argument("-c", "--cardinality", type=int, default=5, metavar="<int>",
            help="Cardinality constraint used during MIQP.")
    p.add_argument("-t", "--threshold", type=float, default=None, metavar="<float>",
            help="Treshold constraint used during MIQP.")
    p.add_argument("-d", "--directory", dest="directory", type=os.path.abspath, 
            default='.', metavar="<dir>",
            help="Directory to store results.")
    p.add_argument("-v", "--verbose", action="store_true",
            help="Be verbose.")
    args = p.parse_args()

    return args


def main():

    args = parse_args()
    mkdir_p(args.directory)
    logging_fname = os.path.join(args.directory, 'qfit_ligand.log') 
    logging.basicConfig(filename=logging_fname, level=logging.INFO)
    if args.verbose:
        console_out = logging.StreamHandler(stream=sys.stdout)
        console_out.setLevel(logging.INFO)
        logging.getLogger('').addHandler(console_out)

    xmap = Volume.fromfile(args.xmap)
    ligand = Ligand.fromfile(args.ligand)
    if args.receptor is not None:
        receptor = Structure.fromfile(args.receptor).select('e', 'H', '!=')
    else:
        receptor = None
    logger.info(' '.join(sys.argv))

    builder = HierarchicalBuilder(
            ligand, xmap, args.resolution, receptor=receptor, 
            build=(not args.no_build), build_stepsize=args.build_stepsize, 
            stepsize=args.stepsize, local_search=(not args.no_local), 
            cardinality=args.cardinality, threshold=args.threshold,
            directory=args.directory, scale=(not args.no_scale),
            )
    builder()

    builder._MIQP(maxfits=args.cardinality, exact=False)
    base = 'conformer'
    builder.write_results(base=base)

    nmax = min(len(builder._coor_set) + 1, 6)
    if args.threshold not in (0, None):
        nmax = min(nmax, int(1.0 / args.threshold))

    for n in xrange(1, nmax):
        builder._MIQP(maxfits=n, exact=True)
        base = 'conformer_{:d}'.format(n)
        builder.write_results(base=base)

