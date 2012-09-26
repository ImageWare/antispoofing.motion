#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Andre Anjos <andre.anjos@idiap.ch>
# Mon 02 Aug 2010 11:31:31 CEST 

"""Calculates the normalized frame differences for face and background, for all
videos of the REPLAY-ATTACK database. This technique is described on the paper:
Counter-Measures to Photo Attacks in Face Recognition: a public database and a
baseline, Anjos & Marcel, IJCB'11.  
"""

import os, sys
import argparse

def main():
  
  import bob
  import numpy
  from xbob.db.replay import Database

  protocols = [k.name for k in Database().protocols()]

  basedir = os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0])))
  INPUTDIR = os.path.join(basedir, 'database')
  OUTPUTDIR = os.path.join(basedir, 'framediff')

  parser = argparse.ArgumentParser(description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('inputdir', metavar='DIR', type=str, default=INPUTDIR,
      nargs='?', help='Base directory containing the videos to be treated by this procedure (defaults to "%(default)s")')
  parser.add_argument('outputdir', metavar='DIR', type=str, default=OUTPUTDIR,
      nargs='?', help='Base output directory for every file created by this procedure defaults to "%(default)s")')
  parser.add_argument('-p', '--protocol', metavar='PROTOCOL', type=str,
      default='grandtest', choices=protocols, dest="protocol",
      help='The protocol type may be specified instead of the the id switch to subselect a smaller number of files to operate on (one of "%s"; defaults to "%%(default)s")' % '|'.join(sorted(protocols)))

  supports = ('fixed', 'hand', 'hand+fixed')

  parser.add_argument('-s', '--support', metavar='SUPPORT', type=str,
      default='hand+fixed', dest='support', choices=supports, help="If you would like to select a specific support to be used, use this option (one of '%s'; defaults to '%%(default)s')" % '|'.join(sorted(supports)))

  # The next option just returns the total number of cases we will be running
  # It can be used to set jman --array option. To avoid user confusion, this
  # option is suppressed # from the --help menu
  parser.add_argument('--grid-count', dest='grid_count', action='store_true',
      default=False, help=argparse.SUPPRESS)

  args = parser.parse_args()

  if args.support == 'hand+fixed': args.support = ('hand', 'fixed')

  from .. import faceloc
  from .. import eval_face_differences, eval_background_differences

  db = Database()

  process = db.objects(protocol=args.protocol, support=args.support)

  if args.grid_count:
    print len(process)
    sys.exit(0)
 
  # if we are on a grid environment, just find what I have to process.
  if os.environ.has_key('SGE_TASK_ID'):
    pos = int(os.environ['SGE_TASK_ID']) - 1
    if pos >= len(process):
      raise RuntimeError, "Grid request for job %d on a setup with %d jobs" % \
          (pos, len(process))
    process = [process[pos]]

  counter = 0
  for obj in process:
    counter += 1
 
    filename = obj.videofile(args.inputdir)
    input = bob.io.VideoReader(filename)
    locations = faceloc.load(obj, args.inputdir)

    sys.stdout.write("Processing file %s (%d frames) [%d/%d]..." % (filename,
      input.number_of_frames, counter, len(process)))

    # start the work here...
    vin = input.load() # load all in one shot.
    prev = bob.ip.rgb_to_gray(vin[0,:,:,:])
    curr = numpy.empty_like(prev)
    data = numpy.zeros((len(vin), 2), dtype='float64')
    data[0] = (numpy.NaN, numpy.NaN)

    for k in range(1, vin.shape[0]):
      bob.ip.rgb_to_gray(vin[k,:,:,:], curr)

      if locations[k] and locations[k].is_valid():
        sys.stdout.write('.')
        data[k][0] = eval_face_differences(prev, curr, locations[k])
        data[k][1] = eval_background_differences(prev, curr, locations[k], None)
      else:
        sys.stdout.write('x')
        data[k] = (numpy.NaN, numpy.NaN)

      sys.stdout.flush()

      # swap buffers: curr <=> prev
      tmp = prev
      prev = curr
      curr = tmp

    obj.save(data, args.outputdir, '.hdf5')
    
    sys.stdout.write('\n')
    sys.stdout.flush()

  return 0

if __name__ == "__main__":
  main()
