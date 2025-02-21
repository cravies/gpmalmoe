import os
import argparse
import gzip as gz
from pathlib import Path
from deap import gp
from matplotlib import pyplot as plt
from gpmalmo import rundata as rd
from gptools.gp_util import output_ind, explore_tree_recursive, draw_trees
from gptools.read_data import read_data
import pandas as pd
from mpl_toolkits.mplot3d import Axes3D

def update_experiment_data(data, ns):
    dict = vars(ns)
    for i in dict:
        setattr(data, i, dict[i])
        # data[i] = dict[i]

warnOnce = False

def try_cache(rundata, hashable, index=0):
    if index==-1:
        return
    rundata.accesses = rundata.accesses + 1
    res = rundata.fitnessCache[index].get(hashable)
    if rundata.accesses % 1000 == 0:
        """
        print("Caches size: " + str(rundata.stores) + ", Accesses: " + str(rundata.accesses) + " ({:.2f}% hit rate)".format(
            (rundata.accesses - rundata.stores) * 100 / rundata.accesses))
        """
    return res


def cachedError(hashable, errorFunc, rundata, args, kargs, index=0):
    # global accesses
    if (not hasattr(rundata,'fitnessCache')) or (rundata.fitnessCache is None):
        if not rundata.warnOnce:
            print("NO CACHE.")
            rundata.warnOnce = True
        return errorFunc(*args, **kargs)

    res = try_cache(rundata, hashable, index)
    if not res:
        res = errorFunc(*args, **kargs)
        rundata.fitnessCache[index][hashable] = res
        rundata.stores = rundata.stores + 1
    # else:
    return res


def init_data(rd):
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--logfile", help="log file path", type=str, default="log.out")
    parser.add_argument("-d", "--dataset", help="Dataset file name", type=str, default="wine")
    parser.add_argument("--dir", help="Dataset directory", type=str,
                        default="/home/lensenandr/datasetsPy/")
    parser.add_argument("-g", "--gens", help="Number of generations", type=int,default=1000)
    parser.add_argument("-od", "--outdir", help="Output directory", type=str, default="./runs")
    parser.add_argument("--erc", dest='use_ercs', action='store_true')
    parser.add_argument("--zeros", dest='use_zeros', action='store_true')
    parser.add_argument("--neighbours", dest="use_neighbours", action="store_true")
    parser.add_argument("--neighbours-mean", dest="use_neighbours_mean", action="store_true")
    parser.add_argument("--trees", dest="max_trees", type=int)
    parser.add_argument("-ob", "--obj", help="objective (time, size, functional)", type=str, default="functional")
    parser.add_argument("-nobj", "--numobj", help="number of objectives", type=int, default=3)
    parser.add_argument("-fs", "--funcset", help="function set", 
        type=str, default="vadd,vsub,vmul,vdiv,max,min,relu,sigmoid,abs")
    parser.add_argument("-oc", "--opcosts", help="node operation costs",
        type=str, default="sum,sum,prod,prod,exp,exp,exp,exp,exp")
    parser.set_defaults(use_ercs=False)
    parser.set_defaults(use_zeros=False)
    parser.set_defaults(use_neighbours=False)
    parser.set_defaults(use_neighbours_mean=False)
    args = parser.parse_args()
    print("ARGS: ",args)
    update_experiment_data(rd, args)
    all_data = read_data("{}{}.data".format(args.dir, args.dataset))
    data = all_data["data"]
    rd.dataset = args.dataset
    rd.nobj = args.numobj
    print("number of objectives: ",rd.nobj)
    rd.num_instances = data.shape[0]
    rd.num_features = data.shape[1]
    rd.labels = all_data["labels"]
    rd.data = data
    rd.data_t = data.T
    rd.objective = args.obj
    rd.function_set = args.funcset.split(',')
    rd.function_costs = args.opcosts.split(',')
    #make dictionary associating node operations with cost
    rd.cost_dict = {k:v for k, v in zip(rd.function_set,rd.function_costs)}
    rd.outdir=args.outdir

def final_output(hof, toolbox, logbook, pop, rundata, pset):
    # grab run number from textfile
    try:
        with open(f'{rd.dataset}_run.txt') as f:
            lines = f.readlines()
            line = lines[-1]
            print("####LINE: ######",line.strip())
            num = line.strip()
            num=int(num)
            num=(num%30+1)
    except FileNotFoundError:
        # it is the initial run
        # i.e no textfile
        num=1
    #now write run# to file
    f = open(f"{rd.dataset}_run.txt", "a")
    f.write(f"{num}\n")
    f.close()
    #set global value
    rd.num = num
    #file to output to
    fname=f"/{rd.dataset}_run_{num}/"
    #make outdir just in case it doesnt exist
    os.makedirs(rd.outdir+fname, exist_ok=True)
    for i,res in enumerate(hof):
        print("iter i: ",i)
        print("fitness values: ",res.fitness.values) 
        output_ind(res, toolbox, rundata, compress=True, out_dir=rd.outdir+fname)
        draw_trees(i, res)
    p = Path(rundata.outdir, rundata.logfile + '.gz')
    with gz.open(p, 'wt') as file:
        file.write(str(logbook))
    pop_stats = [str(p.fitness) for p in pop]
    pop_stats.sort()
    hof_stats = [str(h.fitness) for h in hof]
    fitness_values = [h.fitness.values for h in hof]
    #filter infs 
    fitness_values = [f for f in fitness_values if float('inf') not in f]
    output_pareto_front(fitness_values)
    print("POP:")
    print("\n".join(pop_stats))
    print("PF:")
    print("\n".join(hof_stats))


def output_pareto_front(fitness, output_path="results.csv"):
    """
    Plot the pareto front tradeoff between 
    Neighbourhood structure loss
    "loss"
    And second objective metric
    "second_obj"
    Also write to results database file
    """
    if (rd.nobj==2):
        loss = [f[0] for f in fitness]
        second_obj = [f[1] for f in fitness]
        plt.plot(loss, second_obj)
        plt.xlabel("Accuracy proxy loss")
        plt.ylabel(f"{rd.objective}")
        plt.title(f"Accuracy loss and {rd.objective} \n pareto front")
        plt.tight_layout()
        num = rd.num
        fname=f"/{rd.dataset}_run_{num}/"
        plt.savefig(f"{rd.outdir}{fname}pareto_{rd.dataset}_{num}.png")
    else:
        # 3d pareto surface
        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')
        loss = [f[0] for f in fitness] # neighbourhood structure loss
        second_obj = [f[1] for f in fitness] # tree complexity metric
        third_obj = [f[2] for f in fitness] # embedding dimensionality
        print("results:")
        print(loss,second_obj,third_obj)
        ax.scatter(loss, second_obj, third_obj, linewidth=0.1)
        ax.set_xlabel('$N$')
        ax.set_ylabel('$TC$')
        ax.set_zlabel('$ED$')
        num = rd.num
        fname=f"/{rd.dataset}_run_{num}/"
        fig.savefig(f"{rd.outdir}{fname}pareto_{rd.dataset}_{num}_3d.png")
    #write pareto front to results csv file
    dataframe = {"loss":loss, "second_objective":second_obj, "generations":rd.gens, "metric":rd.objective}
    df = pd.DataFrame(data=dataframe)
    df.to_csv(output_path, mode='a', header=not os.path.exists(output_path))
