from graphmaker.graph import Graph
from rundmcmc.defaults import BasicChain, default_constraints
from rundmcmc.partition import Partition
from rundmcmc.updaters import (votes_updaters, Tally, perimeters, exterior_boundaries,
                               interior_boundaries, boundary_nodes, cut_edges, polsby_popper,
                               cut_edges_by_part)
from rundmcmc.scores import mean_median, mean_thirdian, efficiency_gap
from rundmcmc.run import pipe_to_table
from rundmcmc.output import p_value_report
from rundmcmc.chain import MarkovChain
from rundmcmc.validity import (Validator, within_percent_of_ideal_population,
                               L_minus_1_polsby_popper, UpperBound, no_worse_L_minus_1_polsby_popper)
from rundmcmc.accept import always_accept
from rundmcmc.proposals import propose_random_flip

import sys
import functools
import json
from pprint import pprint

plans = ['2011', 'rounded11', 'Remedial', 'GOV_4_1', 'TS_4_1']
elections = {
    '2016 Presidential': ['T16PRESD', 'T16PRESR'],
    '2016 Senate': ['T16SEND', 'T16SENR']
}


def get_scores(election):
    D, R = elections[election]
    return {
        f"Mean-Median ({election})":
            functools.partial(mean_median, proportion_column_name=f"{D}%"),
        f"Mean-Thirdian ({election})":
            functools.partial(mean_thirdian, proportion_column_name=f"{D}%"),
        f"Efficiency Gap ({election})":
            functools.partial(efficiency_gap, col1=D, col2=R)
    }


def run_pa(plan, total_steps=100000):
    graph = Graph.load('./wes_graph.json').graph

    assignment = {node: graph.nodes[node][plan] for node in graph.nodes}

    updaters = {
        **votes_updaters(elections["2016 Presidential"]),
        **votes_updaters(elections["2016 Senate"]),
        'population': Tally('POP100', alias='population'),
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

    scores = {
        **get_scores('2016 Senate'),
        **get_scores('2016 Presidential'),
        'L^{-1} Polsby-Popper': L_minus_1_polsby_popper
    }

    initial_scores = {key: score(partition)
                      for key, score in scores.items()}

    population_constraint = within_percent_of_ideal_population(partition, 0.01)

    is_valid = Validator(default_constraints +
                         [population_constraint, no_worse_L_minus_1_polsby_popper])

    chain = MarkovChain(propose_random_flip, is_valid,
                        always_accept, partition, total_steps)

    # chain = BasicChain(partition, total_steps=100000)

    table = pipe_to_table(chain, scores)

    initial_scores = {key: score(partition) for key, score in scores.items(
    ) if key != 'L^{-1} Polsby-Popper'}

    table = pipe_to_table(chain, scores)

    fig, axes = plt.subplots(2, 2)

    quadrants = {
        'Mean-Median': (0, 0),
        'Mean-Thirdian': (0, 1),
        'Efficiency Gap': (1, 0),
        'L^{-1} Polsby-Popper': (1, 1)
    }

    for key in scores:
        quadrant = quadrants[key]
        axes[quadrant].hist(table[key], bins=50)
        axes[quadrant].set_title(key)
        axes[quadrant].axvline(x=initial_scores[key], color='r')
    plt.show()

    metadata = {
        'plan': plan,
        'total_steps': total_steps,
        'constraints': [
            'L1 Reciprocal Polsby-Popper no more than 1% worse than the initial plan.',
            'District populations within one percent of ideal.',
            'Districts are contiguous.',
            'No more county splits than the orginal plan.'
        ]
    }

    report = {key: p_value_report(
        key, table[key], initial_scores[key]) for key in scores if key != 'L^{-1} Polsby-Popper'}

    return {**metadata, 'p_value_report': report}


if __name__ == '__main__':
    plan = sys.argv[1]
    report = run_pa(plan)
    pprint(report)

    with open(f"./reports/p_values_{plan}.json", "w") as f:
        json.dump(report, f)
