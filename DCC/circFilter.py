import numpy as np
import os
import sys

import HTSeq

from .IntervalTree import IntervalTree


##########################
#  Input of this script  #
##########################
# This script input a count table:
# chr start end junctiontype count1 count2 ... countn
# and a repeatitive region file in gtf format
# specify minimum circular RNA length


class Circfilter(object):
    def __init__(self, length, countthreshold, replicatethreshold, tmp_dir):
        '''
        counttable: the circular RNA count file, typically generated by findcircRNA.py: chr start end junctiontype  count1 count2 ... countn
        rep_file: the gtf file to specify the region of repeatitive reagion of analyzed genome
        length: the minimum length of circular RNAs
        countthreshold: the minimum expression level of junction type 1 circular RNAs
        '''
        # self.counttable = counttable
        # self.rep_file = rep_file
        self.length = int(length)
        # self.level0 = int(level0)
        self.countthreshold = int(countthreshold)
        # self.threshold0 = int(threshold0)
        self.replicatethreshold = int(replicatethreshold)
        self.tmp_dir = tmp_dir

    # Read circRNA count and coordinates information to numpy array
    def readcirc(self, countfile, coordinates):
        # Read the circRNA count file
        circ = open(countfile, 'r')
        coor = open(coordinates, 'r')
        count = []
        indx = []
        for line in circ:
            fields = line.split('\t')
            # row_indx = [str(itm) for itm in fields[0:4]]
            # print row_indx
            try:
                row_count = [int(itm) for itm in fields[4:]]
            except ValueError:
                row_count = [float(itm) for itm in fields[4:]]
            count.append(row_count)
            # indx.append(row_indx)

        for line in coor:
            fields = line.split('\t')
            row_indx = [str(itm).strip() for itm in fields[0:6]]
            indx.append(row_indx)

        count = np.array(count)
        indx = np.array(indx)
        circ.close()
        return count, indx

    # Do filtering
    def filtercount(self, count, indx):
        print('Filtering by read counts')
        sel = []  # store the passed filtering rows
        for itm in range(len(count)):
            if indx[itm][4] == '0':
                # if sum( count[itm] >= self.level0 ) >= self.threshold0:
                #    sel.append(itm)
                pass
            elif indx[itm][4] != '0':
                if sum(count[itm] >= self.countthreshold) >= self.replicatethreshold:
                    sel.append(itm)

        # splicing the passed filtering rows
        if len(sel) == 0:
            sys.exit("No circRNA passed the expression threshold filtering.")
        return count[sel], indx[sel]

    def read_rep_region(self, regionfile):
        regions = HTSeq.GFF_Reader(regionfile, end_included=True)
        rep_tree = IntervalTree()
        for feature in regions:
            iv = feature.iv
            rep_tree.insert(iv, annotation='.')
        return rep_tree

    def filter_nonrep(self, regionfile, indx0, count0):
        if not regionfile is None:
            rep_tree = self.read_rep_region(regionfile)

            def numpy_array_2_GenomiInterval(array):
                left = HTSeq.GenomicInterval(str(array[0]), int(array[1]), int(array[1]) + self.length, str(array[5]))
                right = HTSeq.GenomicInterval(str(array[0]), int(array[2]) - self.length, int(array[2]), str(array[5]))
                return left, right

            keep_index = []
            for i, j in enumerate(indx0):
                out = []
                left, right = numpy_array_2_GenomiInterval(j)
                rep_tree.intersect(left, lambda x: out.append(x))
                rep_tree.intersect(right, lambda x: out.append(x))
                if not out:
                    # not in repetitive region
                    keep_index.append(i)
            indx0 = indx0[keep_index]
            count0 = count0[keep_index]
        nonrep = np.column_stack((indx0, count0))
        # write the result
        np.savetxt(self.tmp_dir + 'tmp_unsortedWithChrM', nonrep, delimiter='\t', newline='\n', fmt='%s')

    def dummy_filter(self, indx0, count0):
        nonrep = np.column_stack((indx0, count0))
        # write the result
        np.savetxt(self.tmp_dir + 'tmp_unsortedWithChrM', nonrep, delimiter='\t', newline='\n', fmt='%s')

    def removeChrM(self, withChrM):
        print('Remove ChrM')
        unremoved = open(withChrM, 'r').readlines()
        removed = []
        for lines in unremoved:
            if not lines.startswith('chrM') and not lines.startswith('MT'):
                removed.append(lines)
        removedfile = open(self.tmp_dir + 'tmp_unsortedNoChrM', 'w')
        removedfile.writelines(removed)
        removedfile.close()

    def sortOutput(self, unsorted, outCount, outCoordinates, samplelist=None):
        # Sample list is a string with sample names seperated by \t.
        # Split used to split if coordinates information and count information are integrated
        count = open(outCount, 'w')
        coor = open(outCoordinates, 'w')
        if samplelist:
            count.write('Chr\tStart\tEnd\t' + samplelist + '\n')
        lines = open(unsorted).readlines()
        for line in lines:
            linesplit = [x.strip() for x in line.split('\t')]
            count.write('\t'.join(linesplit[0:3] + list(linesplit[6:])) + '\n')
            coor.write('\t'.join(linesplit[0:6]) + '\n')
        coor.close()
        count.close()

    def remove_tmp(self):
        try:
            os.remove(self.tmp_dir + 'tmp_left')
            os.remove(self.tmp_dir + 'tmp_right')
            os.remove(self.tmp_dir + 'tmp_unsortedWithChrM')
            os.remove(self.tmp_dir + 'tmp_unsortedNoChrM')
        except OSError:
            pass
