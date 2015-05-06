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
from gimethod import gimethod_subclasses, GIMethod
from dataset import Dataset, posts2dataset
from sparse_dataset import SparseDataset

logger = logging.getLogger(__name__)

def get_method_by_name(name):
	# get the geoinference class
	candidates = filter(lambda x: x.__name__ == name, gimethod_subclasses())

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
	parser.add_argument('method_name', help='the method to use')
	parser.add_argument('method_settings', help='a json file containing method-specific configurations')
	parser.add_argument('dataset_dir', help='a directory containing a geoinference dataset')
	parser.add_argument('fold_file', help='the name of the file containing information on the cross-validation folds')
	parser.add_argument('results_dir', help='a (non-existent) directory where the evaluation results will be stored')
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
	with open(args.method_settings, 'r') as fh:
		for line in fh:
			setting = json.load(line)
			list_of_settings.append(setting)

	settings = list_of_settings[0]

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
	if location_source is not None:
			training_data = SparseDataset(args.dataset_dir, excluded_users=folds[0], default_location_source=location_source)
	else:
			training_data = SparseDataset(args.dataset_dir, excluded_users=folds[0])


	fold_name = "fold_number"
	fold_users = folds[0]

	# load the method
	method = get_method_by_name(args.method_name)
	method_inst = method()


	# Train on the datset, holding out the testing post IDs
	model = method_inst.train_model(settings, training_data, None)

	logger.debug('Finished training during fold %s; beginning testing' % fold_name)


	logger.debug("Writing results to %s" % (os.path.join(args.results_dir, fold_name + ".results.tsv.gz")))


	for user_id in fold_users:
		posts = [{}]
		locs = model.infer_posts_locations_by_user(user_id, posts)


        logger.debug('Finished testing of fold %s' % fold_name)


if __name__ == '__main__':
	cross_validate()


