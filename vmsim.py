# -*- coding: utf-8 -*-
''' 
Name: 			Deirdre Sweeney <dvs9@pitt.edu>
Date: 			09 November 2014
Class:	 		CS 1550 - Operating Systems
Professor: 		Professor John Misurda 
Project: 		Assignment 3 - VM Simulator
Website: 		http://people.cs.pitt.edu/~jmisurda/teaching/cs1550/2151/cs1550-2151-project3.htm
Description:  	This project will implement four different algorithms for page fault manipulation,
				(optimal, random, not recently used, and clock),

				The program will display the action taken for each memory access: 
					hit, 
					page fault – no eviction, 
					page fault – evict clean, 
					page fault – evict dirty

				It will print out the final results in the following format: 
					Number of frames:       8
					Total memory accesses:  1000000
					Total page faults:      181856
					Total writes to disk:   29401

				It will take as input arguments the following command line:

					./vmsim –n <numframes> -a <opt|clock|nru|rand> [-r <refresh>] <tracefile>

				-n <numframes> 				the number of frames your virtual memory will simulate
				-a <opt|clock|nru|rand> 	the page fault algorithm to run
				-r <refresh> 				the time in terms of memory references in which to refresh the reference bit
				<tracefile>					the .trace file to trace
'''

import sys
import csv
import random
import time
import argparse
from argparse import RawTextHelpFormatter


class PageFaultRunner :
	
	tracefile 		= None
	trace 			= None
	numframes 		= 0
	refresh   		= None
	num_mem_accs    = 0
	page_faults 	= 0
	total_writes 	= 0
	mem_trace		= None

	def __init__(self, tracefile, numframes, refresh) :
		self.tracefile = tracefile
		self.numframes = numframes
		self.refresh   = refresh
		self.trace 	   = []
		self.mem_trace = {}

		trace_reader_obj = open(self.tracefile, 'rbU')
		trace_reader = csv.DictReader(trace_reader_obj, fieldnames=['mem_address', 'ref'], delimiter=' ')
		count = 0
		for line in trace_reader :
			self.trace.append(line)
			if line['mem_address'][0:5] in self.mem_trace :
				self.mem_trace[line['mem_address'][0:5]].append(count)
			else :
				self.mem_trace[line['mem_address'][0:5]] = [count]
			count += 1

	''' 
	Optimal Page Replacement Algorithm: 
	Given you know how the program is going to run, evict the page that is used latest.
	'''
	def runOpt(self) :

		# set variables
		frame_array = [0]*numframes
		dirty_array = [0]*numframes

		for line in self.trace :
			self.num_mem_accs += 1
			page   = line['mem_address'][0:5]
			#offset = line['mem_address'][6:8]
		
			# if hit: 
			if page in frame_array :
				index = frame_array.index(page)
				if (line['ref']=='W') :
					dirty_array[index] = 1
				self.displayAction(0)	

			# if frame array not full
			elif 0 in frame_array :
				index = frame_array.index(0)
				frame_array[index] = page
				dirty_array[index] = 0 if (line['ref']=='R') else 1
				self.displayAction(1)

			# if page fault and must evict
			else : 
				max_frame_index = 0
				findex = frame_array.index

				for frame in frame_array :
				# go through this to find the frame that is furthest out
					if self.mem_trace.has_key(frame) : 
						mem_index = self.mem_trace[frame][0]

						if mem_index > max_frame_index :
							max_frame_index = mem_index
							index = findex(frame)
						
					else :
						max_frame_index = 999999999
						index = findex(frame)
						break

				# if frame to evict is clean
				if (dirty_array[index] == 0) :
					self.displayAction(2)
				else :
					self.displayAction(3) 

				frame_array[index] = page
				dirty_array[index] = 0 if (line['ref']=='R') else 1
			

			if (len(self.mem_trace[line['mem_address'][0:5]]) == 1) :
				del self.mem_trace[line['mem_address'][0:5]]
			else :
				self.mem_trace[line['mem_address'][0:5]].pop(0)

		self.printResults()
		print "Time: " + str(time.time()) + " - " + str(start_time) + " = " + str((time.time()-start_time))

	'''
	Clock Algorithm:
	Make a circular queue ammendment to the second chance algorithm. Evict the last recently used.
	'''
	def runClock(self) :

		# set variables
		frame_array = [0]*self.numframes
		dirty_array = [0]*self.numframes
		ref_array   = [0]*self.numframes
		clock_counter = 0
		eviction = False

		for line in self.trace :
			self.num_mem_accs += 1
			page   = line['mem_address'][0:5]
			offset = line['mem_address'][6:8]

			# if hit :
			if page in frame_array :
				index = frame_array.index(page)
				dirty_array[index] = dirty_array[index] if (line['ref']=='R') else 1
				ref_array[index] = 1
				self.displayAction(0)

			elif 0 in frame_array : #page fault - no eviction
				index = frame_array.index(0)
				frame_array[index] = page
				dirty_array[index] = 0 if (line['ref']=='R') else 1
				ref_array[index] = 1
				self.displayAction(1)

			else : # page fault
				eviction = False
				while not eviction :
					if ref_array[clock_counter] == 0 :
						eviction = True
						if dirty_array[clock_counter] == 0 :
							self.displayAction(2)
						else :
							self.displayAction(3)
						frame_array[clock_counter] = page
						dirty_array[clock_counter] = 0 if (line['ref']=='R') else 1
						ref_array[clock_counter]   = 1
					else : #reference = 1
						eviction = False
						ref_array[clock_counter] = 0
						clock_counter = (clock_counter + 1) % self.numframes

		self.printResults()

	''' 
	Not Recently Used Algorithm:
	Use the R and D bits to evict the page used furthest in the past
	'''
	def runNRU(self) :
		# set frame, dirty, and reference arrays
		frame_array = [0]*self.numframes
		ref_dirty = [(0,0) for temp in range(self.numframes)]
		frames_full = 0
		frame_to_evict = 0

		for line in self.trace :
			self.num_mem_accs += 1

			if (self.num_mem_accs % self.refresh) == 0 :
				ref_dirty = [(0, dirty[1]) for dirty in ref_dirty]

			page = line['mem_address'][0:5]
			offset = line['mem_address'][6:8]

			if (page in frame_array) :
				index = frame_array.index(page)
				ref_dirty[index] = (1, ref_dirty[index][1] if (line['ref'] == 'R') else 1)
				self.displayAction(0)

			elif (frames_full < numframes) :
				frame_array[frames_full] = page
				ref_dirty[frames_full] = (1, 0 if (line['ref']=='R') else 1)
				frames_full += 1
				self.displayAction(1)

			else :

				if (0,0) in ref_dirty :
					frame_to_evict = ref_dirty.index((0,0))
					print "Found (0,0)"
					self.displayAction(2)
				elif (0,1) in ref_dirty :
					frame_to_evict = ref_dirty.index((0,1))
					print "Found (0,1)"
					self.displayAction(3)
				elif (1,0) in ref_dirty :
					frame_to_evict = ref_dirty.index((1,0))
					print "Found (1,0)"
					self.displayAction(2)
				elif (1,1) in ref_dirty :
					frame_to_evict = ref_dirty.index((1,1))
					print "Found (1,1)"
					self.displayAction(3)
				else :
					print "ERROR: UNABLE TO FIND FRAME TO EVICT"

				frame_array[frame_to_evict] = page
				ref_dirty[frame_to_evict] = (1, 0 if (line['ref']=='R') else 1)

		self.printResults()

	'''
	Random Page Replacement Algorithm:
	Pick a page to evict at random.
	'''
	def runRand(self) :
		frame_array = [0]*self.numframes
		dirty_array = [0]*self.numframes
		frames_full = 0

		for line in self.trace :
			self.num_mem_accs += 1

			# evaluate memory access and find page it is from.
			page = line['mem_address'][0:5]
			offset = line['mem_address'][6:]

			# discover if page is in frame array.
			if (page in frame_array) : # Hit
				if (line['ref'] == 'W') :
					dirty_array[frame_array.index(page)] = 1
				self.displayAction(0)

			elif (frames_full < numframes) : # Page frame not full.  
				frame_array[frames_full] = page 
				dirty_array[frames_full] = 0 if (line['ref']=='R') else 1
				frames_full += 1
				self.displayAction(1)

			else : # page fault. must evict 
				index = random.randint(0, numframes-1)

				if (dirty_array[index] == 0) : # page clean
					self.displayAction(2)
				else :
					self.displayAction(3)

				frame_array[index] = page
				dirty_array[index] = 0 if (line['ref']=='R') else 1

		self.printResults()

	def displayAction(self, num, page = None) :
		if   num == 0 :	# 0 = hit
			print "Hit"
		elif num == 1 :
			self.page_faults += 1 
			print "Page fault - no eviction"
		elif num == 2 :
			self.page_faults += 1
			print "Page fault - evict clean" 
		elif num == 3 :
			self.page_faults += 1
			self.total_writes += 1
			print "Page fault - evict dirty"
		else :
			print "WRONG DISPLAY ACTION NUMBER"

	def printResults(self) :
		print "\nNumber of frames : " + str(self.numframes)
		print "Total memory access: " + str(self.num_mem_accs)
		print "Total page faults: " + str(self.page_faults)
		print "Total writes to disk: " + str(self.total_writes) 


# main method
if __name__ == "__main__" :

	start_time = time.time()

	# parse command line
	parser = argparse.ArgumentParser(description='Run and evaluate various page fault algorithms.\n \
				Example use: ./vmsim –n <numframes> -a <opt|clock|nru|rand> [-r <refresh>] <tracefile> \n', \
				formatter_class=RawTextHelpFormatter);

	parser.add_argument('tracefile', )
	parser.add_argument('-n', dest='numframes', type=int, nargs=1, required=True)
	parser.add_argument('-a', dest='algorithm', choices=['opt', 'clock', 'nru', 'rand'], nargs=1, required=True)
	parser.add_argument('-r', dest='refresh', type=int, nargs=1)
	args = parser.parse_args()

	tracefile = args.tracefile
	numframes = args.numframes[0]
	algorithm = args.algorithm[0]
	if args.refresh :
		refresh   = args.refresh[0]
	else :
		refresh = None

	page_fault_runner = PageFaultRunner(tracefile=tracefile, numframes=numframes, refresh=refresh)

	if algorithm == 'opt' :
		page_fault_runner.runOpt()
	elif algorithm == 'clock' :
		page_fault_runner.runClock()
	elif algorithm == 'nru' :
		page_fault_runner.runNRU()
	elif algorithm == 'rand' :
		page_fault_runner.runRand()
	else :
		print "ERROR: UNABLE TO RUN ALGORITHM " + algorithm
		sys.exit(0)
