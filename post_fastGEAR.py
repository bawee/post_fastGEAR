#!/usr/bin/env python3

from Bio import SeqIO
from collections import defaultdict
from collections import OrderedDict
from random import randint
import gzip
from glob import glob
import multiprocessing
import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from glob import glob
import pandas as pd
from Bio import Phylo
import pylab
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import os.path

#added by BW
from matplotlib.ticker import FuncFormatter, MaxNLocator, MultipleLocator, FormatStrFormatter




def main():


    parser = argparse.ArgumentParser(description='make various plots from fastGEAR output')
    parser.add_argument("-i", type=str, help="FastGEAR folder. Should have folders with gene names only no suffix or prefix")
    parser.add_argument("-o", type=str, help="Ouput name")
    parser.add_argument("-g", type=str, help="Genes of interest GOI list. Can be comma separated after flag GOI1,GOI2,GOI3 or a file.txt with one GOI per line. GOIs need to be named exactly as per fastGEAR run", default = None)
    parser.add_argument("-b", type=str, help="Sample of interest SOI list. Can be comma separated after flag SOI1,SOI2,SOI3 or a file.txt with one SOI per line. SOIs need to be named exactly as per fastGEAR run", default = None)
    parser.add_argument("-t", type=int, help="Threads")
    parser.add_argument("-y", type=int, help="Minimum y value to display gene name in scatter plot", default = 4)
    parser.add_argument("-x", type=int, help="Minimum x value to display gene name in scatter plot", default = 4)
    parser.add_argument("-s", type=str2bool, help="Make scatter plot of recent Vs ancestral recombinations", default = True)
    parser.add_argument("-z", type=str2bool, help="Make heatmap of recombinations. Default True", default = True)
    parser.add_argument("-u", type=str2bool, help="Make recombinations per gene plot. Default True", default = True)
    parser.add_argument("-a", type=str2bool, help="Include ancestral recombination. Default True", default = True)
    parser.add_argument("-r", type=str2bool, help="Exclude genes that had no recombination. Default True", default = True)
    parser.add_argument("-p", type=str, help="Tree file for sample order OR txt file of samples in order one per line must end in .txt or will parse as tree file.")
    parser.add_argument("-d", type=int, help="Division factor to draw ticks in heatmap", default = 10)

    args = parser.parse_args()

    #plot heatmap
    MaxYaxis, height, order = parse_tree(args) #BW added MaxYaxis
    gene_len_dict = parse_genes(args)
    genes = list(gene_len_dict.keys())
    most_common_lineage = lineage(args, genes)
    print ('most_common_lineage', most_common_lineage)
    yellow = '#fff822' #most common - background
    # colors = ['blue','red','green','#e6194b','#f58231','#911eb4','#46f0f0','#f032e6',
    #           '#d2f53c','#fabebe','#008080','#e6beff','#aa6e28',
    #            '#808000','#000080','#808080','#000000','#aaffc3']#as distaninct as possible
    #Bryan added the following colors from colorbrewer2.org
    colors = ['#1f78b4','#e31a1c','#33a02c','#ff7f00','#6a3d9a','#b15928','#aa6e28','#a6cee3','#fb9a99','#b2df8a','#fdbf6f','#f58231','#cab2d6',
               '#808000','#000080','#808080','#000000','#aaffc3']#as distaninct as possible
    colors.insert(int(most_common_lineage), yellow)

    if args.z:
        print ('making heatmap...')
        #instanciate plot

        fig = plt.figure(figsize=(10, 10), dpi =300) #changed 50,50 to 50,100 BW
        # ax = fig.add_subplot(111, aspect='equal') # Default (x,y), width, height
        ax = fig.add_subplot(111, aspect='0.3') # Default (x,y), width, height #BW aspect 0.3 makes the heatmap in landscape orientation
        print("height: " + str(MaxYaxis) + ", cumulativeLen: " + str(cumulativeLen)) #BW

        for i in range(0, len(genes), args.t):
            tmp = genes[i:i+args.t]
            tmp = [(gene, args, gene_len_dict, height, order, colors) for gene in tmp]
            p = multiprocessing.Pool(processes = args.t)
            tmp_genes = p.map(make_patches, tmp)
            p.close()
            for gene_patch_list in tmp_genes:
                for gene_patch in gene_patch_list:
                    ax.add_patch(gene_patch)

        #BW Divide x axis by number of fractions given by -d flag
        divisionFactor = args.d
        ax.xaxis.set_major_locator(MultipleLocator(1/divisionFactor)) #Sets ticks at intervals of given by -d.
        ax.set_xticklabels(frange((0-(cumulativeLen/divisionFactor)), cumulativeLen, cumulativeLen/divisionFactor), fontsize=8, rotation='vertical')

        ax.yaxis.set_major_locator(MultipleLocator(1/MaxYaxis)) #BW Sets ticks to match the number of taxa
        ax.set_yticklabels(frange(0, MaxYaxis, 1/MaxYaxis), fontsize=0) #Sets labels for y-axis to invisible (size 0)

        fig.savefig(args.o + '_heat.svg', dpi=300, bbox_inches='tight') #BW changed to svg
        plt.close('all')

    if args.u:
        print ('Making recombination count plot')
        recombinations = defaultdict(int)
        for i in range(0, len(genes), args.t):
            chunk = genes[i:i+args.t]
            recent_recombinations_sets = scatter_multi('recent', i, args, chunk)
            for gene_recent, recent_recombinations in recent_recombinations_sets:
                recombinations[gene_recent] += len(recent_recombinations)
            if args.a:
                ancestral_recombinations_sets = scatter_multi('ancestral', i, args, chunk)
                for gene_ancestral, ancestral_recombinations in ancestral_recombinations_sets:
                    recombinations[gene_ancestral] += len(ancestral_recombinations)
        #instanciate plot
        fig = plt.figure(figsize=(50, 50), dpi =300)
        ax = fig.add_subplot(111, aspect='equal') # Default (x,y), width, height
        #legend
        legend = []
        for i in range(8):#might need to make this dynamic...
            c=colors[i]
            i+=1.0
            i/=10.0
            p = patches.Rectangle((0.5, i), 0.1, 0.05, facecolor=c,edgecolor='black')
            legend.append(p)
        plt.legend(legend, ['0-4', '5-9', '10-14','15-19', '20-24','25-29','30-34','35-40'], fontsize=55)
        for gene in recombinations:
            total_length = sum(list(gene_len_dict.values()))
            x, total_length_so_far, gene_len_percent = get_coords(args, gene_len_dict, gene, total_length)
            count = recombinations.get(gene)
            if count in list(range(0,5)):
                c=colors[0]
            elif count in list(range(5,10)):
                c=colors[1]
            elif count in list(range(10,15)):
                c=colors[2]
            elif count in list(range(15,20)):
                c=colors[3]
            elif count in list(range(20,25)):
                c=colors[4]
            elif count in list(range(25,30)):
                c=colors[5]
            elif count in list(range(30,35)):
                c=colors[6]
            elif count in list(range(35,40)):
                c=colors[7]
            else:
                print ('number of recombinations exceeds codes ability to color!!!', count)
            if count == 0:
                height = 0.0
            else:
                height = (float(count)/2.0)*0.01
            p = patches.Rectangle((x, 0.0), gene_len_percent, height, facecolor=c,edgecolor=None)
            ax.add_patch(p)
        plt.title('Recombinations per ' + str(len(recombinations)) + ' gene')
        plt.savefig(args.o + '_recombination_count.png', dpi=300, bbox_inches='tight')
        plt.close('all')
    if args.s:
        print ('Getting recombinations per gene')
        #plot recent (y) Vs ancestral (x) on scatter plot
        data = {'x':[], 'y':[], 'gene':[]}
        for i in range(0, len(genes), args.t):
            chunk = genes[i:i+args.t]
            recent_recombinations_dicts = scatter_multi('recent', i, args, chunk)
            ancestral_recombinations_dicts = scatter_multi('ancestral', i, args, chunk)
            for gene_recent, recent_recombinations_dict in recent_recombinations_dicts:
                  data['y'].append(len(recent_recombinations_dict))
                  data['gene'].append(gene_recent)
            for j, tmp_tuple in enumerate(ancestral_recombinations_dicts):
                  gene_ancestral, ancestral_recombinations_dict = tmp_tuple
                  try: assert data['gene'][i+j] == gene_ancestral
                  except: print (data['gene'][i+j], gene_ancestral)
                  data['x'].append(len(ancestral_recombinations_dict))
        # display scatter plot data
        plt.figure(figsize=(15,15)) #BW
        plt.title('FastGEAR ancestral Vs recent recombinations', fontsize=20)
        plt.xlabel('Ancestral', fontsize=15)
        plt.ylabel('Recent', fontsize=15)
        plt.xticks(list(range(len(data.get('x')))))
        plt.yticks(list(range(len(data.get('y')))))
        plt.scatter(data['x'], data['y'], marker = 'o')
        # add labels
        for label, x, y in zip(data['gene'], data['x'], data['y']): #Mimum number of ancestral vs recent recombinations to display gene labels
            if x > int(args.x) and y > int(args.y):
                print(label) #Print out labels to screen that meet the threshold - BW
                plt.annotate(label, xy = (x, y), fontsize=6, xytext=(-10, 10), textcoords='offset pixels') #

        plt.savefig(args.o + '_scatter.png', dpi=300, bbox_inches='tight')
        plt.close('all')

def str2bool(v):

    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def scatter_multi(when, i, args, tmp):

    tmp = [(args, gene, when) for gene in tmp]
    p = multiprocessing.Pool(processes = args.t)
    recombinations_dicts = p.map(count_recombinations, tmp)
    p.close()

    return recombinations_dicts

def make_patches(tuple_of_args):

    '''
    Calculate all patches
    '''

    gene, args, gene_len_dict, height, order, colors = tuple_of_args
    recent_recombinations_dict = get_recombinations(args, gene, 'recent')
    ancestral_recombinations_dict = get_recombinations(args, gene, 'ancestral') #-no strain name details

    # recombinations_dict['gene1']['gene'] = gene #BW
    # recombinations_dict['gene1']['age'] = age #BW
    # table = pd.DataFrame(recent_recombinations_dict) #BW
    # table.to_csv('pandas_out.csv', mode='a') #BW
    # #table.to_csv('pandas_out.csv') #BW
    # print("Processing " + age) #BW
    # print("Processing... " + gene) #BW
    # print("Printing to csv using pandas...") #BW

    lineages = base_lineage(args, gene)
    # print("Lineages for  " + gene) # + " is " + lineages) #BW
    # table = pd.Series(lineages) #BW
    # table.to_csv('pandas_out.csv', mode='a') #BW


    gene_len = gene_len_dict.get(gene)
    total_length = sum(list(gene_len_dict.values()))
    x, total_length_so_far, gene_len_percent = get_coords(args, gene_len_dict, gene, total_length)
    y = 1.0
    patches_list = []
    width = 1.5/float(len(order))
    for j, sample in enumerate(order):
        if sample in lineages:
            c = colors[lineages.get(sample)]
            p = patches.Rectangle((x, y - height), gene_len_percent, height, facecolor=c,edgecolor='black', linewidth=width ) #(x,y), width, height
            patches_list.append(p)
            if len(ancestral_recombinations_dict) > 0:#identify the strains in the recipient lineage - lineage2 == lineages.get(sample)
                if int(ancestral_recombinations_dict.get('all').get('lineage2')) == int(lineages.get(sample)):
                    c = colors[int(ancestral_recombinations_dict.get('all').get('lineage1'))]#use color of donor lineage
                    patches_list = overlay_recombinations(ancestral_recombinations_dict, 'all', x, total_length, height, y, patches_list, width, c)
            if sample in recent_recombinations_dict:#recent ontop of ancestral
                c = colors[recent_recombinations_dict.get(sample).get('donor_lineage')]
                patches_list = overlay_recombinations(recent_recombinations_dict, sample, x, total_length, height, y, patches_list, width, c)
        y -= height


    return patches_list

def overlay_recombinations(recombinations_dict, sample, x, total_length, height, y, patches_list, width, c):

    start = recombinations_dict.get(sample).get('start')
    tmp_x =  x + (start/total_length)
    end = recombinations_dict.get(sample).get('end')
    recombination_len = (x + (end/total_length)) - tmp_x
    p = patches.Rectangle((tmp_x, y - height), recombination_len, height, facecolor=c, edgecolor='black', linewidth=width)
    patches_list.append(p)

    return patches_list

def parse_list(arg):

    if ',' in arg:
        GOI = arg.strip().split(',')
    else:
        GOI=[]
        with open(arg, 'r') as fin:
            for line in fin:
                GOI.append(line.strip())
    return GOI

def parse_tree(args):

    '''
    Get the order of sample in the tree
    '''

    if args.b:
       SOI = parse_list(args.b)
    order = []
    if args.p.endswith('.txt'):
        with open(args.p, 'r') as fin:
            for line in fin:
                order.append(line.strip())
    else:
        t = Phylo.read(args.p, 'newick')
        t.ladderize()#branches with fewer leaf nodes are displayed on top - as per itol
        for node in t.find_clades():
            if node.name:
                if args.b:
                    if node.name in SOI:
                        order.append(node.name)
                else:
                    order.append(node.name)
        print ('Number of samples in tree: ', len(order))
        if args.b:
            last_sample_in_SOI = sorted(list(SOI))[-1]
            try:  assert len(SOI) == len(order)
            except: print ('Your sample names dont match those in the tree!!!! tree = ', node.name, 'ur input = ', last_sample_in_SOI)
        #PLot
        fig = plt.figure(figsize=(15, 55), dpi =300)
        ax = fig.add_subplot(111)
        Phylo.draw(t, do_show=False, axes=ax)
        pylab.axis('off')
        pylab.rcParams.update({'font.size': 0.5})
        pylab.savefig(args.o+'_tree.png',format='png', bbox_inches='tight', dpi=300)
        plt.close('all')
        #write
        with open('order_of_samples_from_tree.txt', 'w') as fout:
            for sample in order:
                fout.write(sample + '\n')
    height = 1.00/len(order)

    MaxYaxis = len(order) # BW Get Y axis maximum value

    return MaxYaxis, height, order

def parse_genes(args):

    '''
    Parse fastGEAR output folder
    '''
    if args.g:
        GOI = parse_list(args.g)
    if args.g:
        genes_output_folders = []
        for gene in GOI:
            genes_output_folders.append(args.i + '/' + gene)
    else:
        genes_output_folders = glob(args.i + '/*')
    gene_len_dict = OrderedDict()

    for i, gene_path in enumerate(genes_output_folders):
        if os.path.isfile(gene_path+'/output/recombinations_recent.txt'):
            if os.path.isfile(gene_path+'/output/lineage_information.txt'):
                with open(gene_path+'/output/recombinations_recent.txt', 'r') as fin:
                    if fin.readline().strip() == '0 RECENT RECOMBINATION EVENTS':
                        if not args.a:# skip if ancestral = Fasle
                            continue

                gene = gene_path.strip().split('/')[-1]
                if args.g:
                    if gene not in GOI:
                        continue
                for record in SeqIO.parse(gene_path + '/' + gene + '.fa','fasta'):
                    gene_len_dict[gene] = len(str(record.seq))
                    break
            else:
                print ('missing a file!!!!!!!!!!!!',gene_path+'/output/lineage_information.txt')
        else:
            print ('missing a file!!!!!!!!!!!!',gene_path+'/output/recombinations_recent.txt')

    if args.g:
        input_gene = sorted(list(GOI))[0] #BW: Just takes the first in the list. Does not really do the job of showing that 2 lists are different.
        try:  assert len(GOI) == len(gene_len_dict)
        except: print ('Your gene names dont match those in fastGEAR!!!! fastGEAR = ', str(len(gene_len_dict)), 'example gene = ',gene,'ur input = ', str(len(GOI)), 'example gene = ', input_gene)
    print ('Number of genes is', len(gene_len_dict))
    #write
    global cumulativeLen #BW declare global cumulativeLen variable so that it can be used for the heatmap Y-axis
    cumulativeLen = 0

    with open('order_and_length_of_genes.txt', 'w') as fout:
        for gene in gene_len_dict:
            cumulativeLen = cumulativeLen + gene_len_dict.get(gene) #BW
            fout.write(gene + '\t' + str(gene_len_dict.get(gene)) +'\t' + str(cumulativeLen) + '\n') #BW added cumulativeLen
    return gene_len_dict


def get_coords(args, gene_len_dict, gene, total_length):

    '''
    Get x coordinates
    '''
    gene_len = gene_len_dict.get(gene)
    gene_len_percent = gene_len/total_length
    total_length_so_far = 0
    x = 0.0
    gene_len = gene_len_dict.get(gene)
    total_length = sum(list(gene_len_dict.values()))
    for previous_gene in gene_len_dict:
        if previous_gene == gene:
            break
        previous_gene_len = gene_len_dict.get(previous_gene)
        previous_gene_len_percent = previous_gene_len/total_length
        total_length_so_far += previous_gene_len
        x += previous_gene_len_percent

    return x, total_length_so_far, gene_len_percent



def count_recombinations(tuple_of_args):

    args, gene, recent_or_ancestral = tuple_of_args
    #get recombination counts (start end are same)
    if args.b:
        SOI = parse_list(args.b)
    recombinations_dict = defaultdict(int)#this mays well be a set - never use teh count...
    if os.path.isfile(args.i + '/' + gene + '/output/recombinations_' + recent_or_ancestral + '.txt'):
        with open(args.i + '/' + gene + '/output/recombinations_' + recent_or_ancestral + '.txt', 'r') as fin:
            fin.readline()#RECOMBINATIONS IN LINEAGES
            fin.readline()#Start End Lineage1 Lineage2 log(BF)
            for line in fin:
                if recent_or_ancestral == 'recent':
                    start, end, donor_lineage, recipient_strain, _, strain_name = line.strip().split()
                    if args.b:
                        if strain_name in SOI:
                            recombinations_dict[start + ':' + end] += 1
                    else:
                        recombinations_dict[start + ':' + end] += 1
                if recent_or_ancestral == 'ancestral':
                    start, end, l1, l2, _ = line.strip().split()
                    recombinations_dict[start + ':' + end] += 1
    return (gene, recombinations_dict)

def bits(line, recombinations_dict):

    start, end, donor_lineage, recipient_strain, _, strain_name = line.strip().split()
    sample = strain_name
    recombinations_dict[sample]['start'] = float(start)
    recombinations_dict[sample]['end'] = float(end)
    recombinations_dict[sample]['donor_lineage'] = int(donor_lineage)
    recombinations_dict[sample]['recipient_strain'] = recipient_strain

    return recombinations_dict

def get_recombinations(args, gene, age):

    '''
    from Pekka
     The way I draw the recombinations:
    1) For each ancestral recombination: identify the strains in the recipient lineage (this is assumed to be lineage 2, as it is the smaller one). Draw a segment in each of these strains, using the color of the donor lineage (Lineage 1).
2) For each recent recombination: draw a segment in the recipient, using the color of the donor lineage.

    Note that the recent recombinations should be on top of the ancestral ones. (Of course one could draw just one or the other)
    '''
    #get  recombinations

    if args.g:
        GOI = parse_list(args.g)
    if os.path.isfile(args.i + '/' + gene + '/output/recombinations_' + age + '.txt'):
        with open(args.i + '/' + gene + '/output/recombinations_' + age + '.txt', 'r') as fin:
            recombinations_dict = defaultdict(lambda: defaultdict(str))
            fin.readline()
            fin.readline()#Start End DonorLineage RecipientStrain log(BF) StrainName
            for line in fin:
                if age == 'recent':
                    start, end, donor_lineage, recipient_strain, _, strain_name = line.strip().split()
                    if args.g: #BW
                        if gene in GOI:   #BW changed "strain_name" to "gene"
                            recombinations_dict = bits(line, recombinations_dict)
                    else:
                        recombinations_dict = bits(line, recombinations_dict)
                if age == 'ancestral':
                    start, end, l1, l2, _ = line.strip().split()
                    recombinations_dict['all']['start'] = float(start)
                    recombinations_dict['all']['end'] = float(end)
                    recombinations_dict['all']['lineage1'] = int(l1)#donor
                    recombinations_dict['all']['lineage2'] = int(l2)#recipient

        return recombinations_dict

def base_lineage(args, gene):

    #get base lineage
    lineages = defaultdict(int)
    if os.path.isfile(args.i + '/' + gene + '/output/lineage_information.txt'):
        with open(args.i + '/' + gene + '/output/lineage_information.txt', 'r') as fin:
            fin.readline() #'StrainIndex', 'Lineage', 'Cluster', 'Name'
            for line in fin:
                strain_index, lineage, cluster, name = line.strip().split()
                sample = name.split('.')[0] #Removes any suffix. make more generic
                lineages[sample] = int(lineage)
    else:
        print (gene +' has no base lineage_information.txt')

    return lineages

def lineage(args, genes):

    #get base lineage
    lineages = defaultdict(int)
    for gene in genes:
        if os.path.isfile(args.i + '/' + gene + '/output/lineage_information.txt'):
            with open(args.i + '/' + gene + '/output/lineage_information.txt', 'r') as fin:
                fin.readline() #'StrainIndex', 'Lineage', 'Cluster', 'Name'
                for line in fin:
                    strain_index, lineage, cluster, name = line.strip().split()
                    sample = name.split('.')[0] #Removes any suffix. make more generic
                    lineages[lineage] +=1
        else:
            print (gene +' has no lineage_information.txt')
    count = 0
    for lineage in lineages:
        if lineages.get(lineage) > count:
            biggest = lineage
            count = lineages.get(lineage)
    return biggest

#Functions added by BW - to relabel axes
def format_fn(tick_val, tick_pos):
    if int(tick_val) in xs:
        return labels[int(tick_val)]
    else:
        return ''

def frange(start, stop, step):
    i = start
    while i < stop:
        yield int(i) #BW used int(i) to get rounded numbers
        i += step

if __name__ == "__main__":
    main()
