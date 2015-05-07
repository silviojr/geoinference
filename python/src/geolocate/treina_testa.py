##
#  Copyright (c) 2015, Derek Ruths, David Jurgens
#
#  All rights reserved. See LICENSE file for details
##
import argparse
import json
import simplejson
import jsonlib
import logging
import os, os.path
import datetime
import gzip
import time

from collections import defaultdict
from gimethod import GIMethod, gimethod_subclasses
from dataset import Dataset, posts2dataset
from my_sparse_dataset import SparseDataset
from geolocate import *
logger = logging.getLogger(__name__)

def get_method_by_name(name):
	# get the geoinference class
	#print "candidatos: %s" %
	gimethod_subclasses()
	candidates =  GIMethod.__subclasses__()
	print [x.__name__ for x in candidates]
	candidates = filter(lambda x: x.__name__ == name, candidates)

	if len(candidates) == 0:
		logger.fatal('No geoinference named "%s" was found.' % name)
		logger.info('Available methods are: %s' % ','.join([x.__name__ for x in gimethod_subclasses()]))
		quit()

	if len(candidates) > 1:
		logger.fatal('More than one geoinference method named "%s" was found.')
		quit()

	return candidates[0]

def ls_methods(args):
	"""
	Print out the set of methods that the tool knows about.
	"""
	for x in gimethod_subclasses():
		print '\t' + x.__name__ 


def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
	yield l[i:i+n]

def cross_validate():
	parser = argparse.ArgumentParser(prog='geoinf cross_validate', description='evaluate a geocinference method using cross-validation')
	parser.add_argument('-f', '--force', help='overwrite the output model directory if it already exists')
	parser.add_argument('--method_name', help='the method to use')
	parser.add_argument('--method_settings', help='a json file containing method-specific configurations. Each confiration in a line')
	parser.add_argument('--users_file', help='a directory containing a geoinference dataset')
	parser.add_argument('--bi_network_file', help='file containing bidirectional network')
	parser.add_argument('--network_file', help='a file containing a direcitonal network')
	parser.add_argument('--fold_file', help='the name of the file containing information on the cross-validation folds. One fold per line. Each line contains users ids separated by spaces')
	parser.add_argument('--results_dir', help='a (non-existent) directory where the evaluation results will be stored')
	parser.add_argument('--fold', nargs=1,
                            help='runs just that fold from the cross-fold dataset')
	parser.add_argument('--location-source', nargs=1,
                            help='specifies the source of ground-truth locations')

	args = parser.parse_args()

	# confirm that the output directory doesn't exist
#	if os.path.exists(args.results_dir) and not args.force:
#		raise Exception, 'output results_dir cannot already exist'

	try:
		os.makedirs(args.results_dir)
	except:
		pass


	# load the data
	list_of_settings = []
	try:
		with open(args.method_settings, 'r') as fh:
			for line in fh:
				setting = json.loads(line.strip())
				list_of_settings.append(setting)
	except Exception,e:
		print e
		pass
	#make sure there exists at least one empty setting
	if len(list_of_settings) == 0:
		list_of_settings.append({})


	for settings in list_of_settings:
		print "=======================SETTINGS: %s==============================" % settings
		location_source = args.location_source
		if location_source:
				logger.debug('Using %s as the source of ground truth location' % location_source)
				location_source = location_source[0]
				settings['location_source'] = location_source


		# Load the folds to be used in the dataset
		folds_fh = open( args.fold_file )

		# Each line contains the user IDs to be held out
		# from the full dataset (for that fold) and the corresponding file in
		# the fold_dir containing the testing data for that fold
		folds = []
		for line in folds_fh:
			users_to_held_out = set(line.strip().split())
			folds.append(users_to_held_out)

		# load the dataset
		training_data = None
		'''
		if location_source is not None:
				training_data = SparseDataset(args.dataset_dir, excluded_users=folds[0], default_location_source=location_source)
		else:
				training_data = SparseDataset(args.dataset_dir, excluded_users=folds[0])
		'''


		method_results_dir = "metodo=%s" % args.method_name.split("_")[0]
		for setting_field in settings:
			method_results_dir += "-%s=%s" % (setting_field, settings[setting_field])

		if args.network_file:
			training_data = SparseDataset(settings = settings,
			                              location_users_file=args.users_file,
			                              network_file=args.network_file)
			method_results_dir += "-network=%s" % args.network_file

		if args.bi_network_file:
			training_data = SparseDataset(settings = settings,
			                              location_users_file=args.users_file,
			                              bi_network_file=args.bi_network_file)
			method_results_dir += "-binetwork=%s" % args.bi_network_file.split("/")[-1]


		try:
			os.makedirs(os.path.join(args.results_dir, method_results_dir))
		except:
			pass

		for fold_number, fold_users in enumerate(folds):

			fold_name = "fold_%s" % fold_number


			training_data.set_excluded_users(fold_users)

			# load the method
			method = get_method_by_name(args.method_name)
			method_inst = method()


			# Train on the datset, holding out the testing post IDs
			model = method_inst.train_model(settings, training_data, None)

			logger.debug('Finished training during fold %s; beginning testing' % fold_name)


			logger.debug("Writing results to %s" % (os.path.join(args.results_dir, fold_name )))



			output_file = open( os.path.join(args.results_dir, method_results_dir , "fold_%s" % fold_number), "w")
			total_fold = len(fold_users)
			preditos = 0
			acertos = 0
			logger.debug("Tamanho do teste: %s" % total_fold)
			for user_id in fold_users:
				post = {"user":{"id_str":user_id, "id":user_id}}
				locs = model.infer_post_location(post)
				if locs is None:
					continue
				preditos += 1
				lat_p, lon_p = locs
				lat, lon = training_data._users_real_locations[user_id]
				if (lat_p, lon_p) == (lat, lon):
					acertos += 1
				output_file.write("%s;%s;%s;%s;%s\n" % (user_id, lat_p, lon_p, lat, lon))
			output_file.close()
			logger.debug('Finished testing of fold %s' % fold_name)
			print "%s preditos, %s acertos. Precision: %s, Recall: %s" %(preditos, acertos, acertos/float(preditos), preditos/float(total_fold) )


if __name__ == '__main__':
	logging.basicConfig(level="DEBUG", format='%(message)s')
	cross_validate()


