from graphmaker.graph import Graph
from rundmcmc.defaults import BasicChain, default_constraints
from rundmcmc.partition import Partition
from rundmcmc.updaters import (votes_updaters, Tally, perimeters, exterior_boundaries,
                               interior_boundaries, boundary_nodes, cut_edges, polsby_popper,
                               cut_edges_by_part)
from rundmcmc.scores import mean_median, mean_thirdian, efficiency_gap
from rundmcmc.output import p_value_report, ChainOutputTable
from rundmcmc.chain import MarkovChain
from rundmcmc.validity import (Validator, within_percent_of_ideal_population,
                               L_minus_1_polsby_popper, UpperBound, SelfConfiguringLowerBound)
from rundmcmc.accept import always_accept
from rundmcmc.proposals import propose_random_flip_no_loops

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import pathlib
import datetime
import math
import sys
import functools
import json
from pprint import pprint

plans = ['2011', 'Remedial', 'GOV_4_1', 'TS_4_1']
elections = {
    '2016_Presidential': ['T16PRESD', 'T16PRESR'],
    '2016_Senate': ['T16SEND', 'T16SENR']
}

now = datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")


def distance_from_ideal_population(partition):
    populations = partition['population'].values()
    ideal = sum(populations) / len(populations)
    return math.sqrt(sum((value - ideal)**2 for value in populations))


def how_many_seats(col1, col2):
    def function(partition):
        return sum(partition[col1][part] > partition[col2][part] for part in partition.parts)
    return function


def pipe_to_table(chain, handlers, display=True, number_of_reports=100):
    table = ChainOutputTable()
    display_interval = math.floor(len(chain) / number_of_reports)
    counter = 0
    with open(f"./logs/flips_{now}.log", 'w') as f:
        f.write("{ \"flips\": [\n")
        for state in chain:
            row = {key: handler(state) for key, handler in handlers.items()}
            table.append(row)
            f.write(json.dumps(state.flips) + ",")
            if counter % display_interval == 0:
                if display:
                    print(f"Step {counter}")
                    print(row)
            counter += 1
        f.write("\n]\n}\n")
    return table


def get_scores(election):
    D, R = elections[election]
    return {
        f"Mean-Median_({election})":
            functools.partial(mean_median, proportion_column_name=f"{D}%"),
        f"Mean-Thirdian_({election})":
            functools.partial(mean_thirdian, proportion_column_name=f"{D}%"),
        f"Efficiency_Gap_({election})":
            functools.partial(efficiency_gap, col1=D, col2=R),
        f"How_Many_D_Seats_({election})":
            how_many_seats(D, R)
    }


def set_up_chain(plan, total_steps, adjacency_type='queen'):
    graph = Graph.load(f"./PA_{adjacency_type}.json").graph

    assignment = {node: graph.nodes[node][plan] for node in graph.nodes}

    updaters = {
        **votes_updaters(elections["2016_Presidential"]),
        **votes_updaters(elections["2016_Senate"]),
        'population': Tally('population', alias='population'),
        'perimeters': perimeters,
        'exterior_boundaries': exterior_boundaries,
        'interior_boundaries': interior_boundaries,
        'boundary_nodes': boundary_nodes,
        'cut_edges': cut_edges,
        'areas': Tally('area', alias='areas'),
        'polsby_popper': polsby_popper,
        'cut_edges_by_part': cut_edges_by_part
    }

    partition = Partition(graph, assignment, updaters)

    population_constraint = within_percent_of_ideal_population(partition, 0.01)
    compactness_constraint = SelfConfiguringLowerBound(
        L_minus_1_polsby_popper, epsilon=0.01)

    is_valid = Validator(default_constraints +
                         [population_constraint])

    return partition, MarkovChain(propose_random_flip_no_loops, is_valid,
                                  always_accept, partition, total_steps)


def run_pa(plan, total_steps=1000000):
    partition, chain = set_up_chain(plan, total_steps)

    scores = {key: value for election in elections for key,
              value in get_scores(election).items()}

    # scores['Distance_From_Ideal_Population'] = distance_from_ideal_population

    scores['L_minus_1_Polsby-Popper'] = L_minus_1_polsby_popper

    initial_scores = {key: score(partition)
                      for key, score in scores.items()}

    table = pipe_to_table(chain, scores)

    pathlib.Path('./plots/{plan}/{now}').mkdir(parents=True, exist_ok=True)

    for score in scores:
        if 'Efficiency' in score:
            plt.xlim(0.0, 0.30)
        elif 'Mean-Median' in score:
            plt.xlim(0.0, 0.60)
        plt.hist(table[score], bins=100)
        plt.title(score.replace('_', ' '))
        plt.axvline(x=initial_scores[score], color='r')
        plt.savefig(f"./plots/{plan}/{now}/{score}.svg")
        plt.close()

    metadata = {
        'plan': plan,
        'total_steps': total_steps
    }

    report = {key: p_value_report(
        key, table[key], initial_scores[key]) for key in scores if key != 'L_minus_1_Polsby-Popper'}

    return {**metadata, 'p_value_report': report}


if __name__ == '__main__':
    plan = sys.argv[1]
    report = run_pa(plan)
    pprint(report)

    with open(f"./reports/p_values_{plan}.json", "w") as f:
        json.dump(report, f)
