import os
import sys

input_dir = sys.argv[1]
method_name = sys.argv[2]
output_dir = sys.argv[3]
try:
	settings_file = sys.argv[4]
except:
	settings_file = "None"


current_path = os.path.dirname(os.path.abspath(__file__))
upper_path = "/" + "/".join(current_path.split("/")[:-1])
print "export PYTHONPATH=%s" % upper_path
for arq_name in os.listdir(input_dir):
    if 'edge' not in arq_name:
        continue
    arq_path = os.path.join(input_dir, arq_name)
    
    print "python treina_testa.py  --method_name %s --method_settings %s --users_file /scratch/silviojr/mestrado/github/mestrado/data/usuarios_coordenadas_cluster_1800 --bi_network_file %s --fold_file /scratch/silviojr/mestrado/github/mestrado/folds/10_folds_min_1800_users_dist_0.txt --results_dir %s" % (method_name, settings_file, arq_path, output_dir)