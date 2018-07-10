from graphmaker.graph import Graph
from rundmcmc.defaults import BasicChain
from rundmcmc.partition import Partition
from rundmcmc.updaters import (votes_updaters, Tally, perimeters, exterior_boundaries,
                               interior_boundaries, boundary_nodes, cut_edges, polsby_popper,
                               cut_edges_by_part)
from rundmcmc.scores import mean_median, mean_thirdian, efficiency_gap
from rundmcmc.run import pipe_to_table
from rundmcmc.output import p_value_report

import functools
import pprint


def run_pa(plan='TS_4_1'):
    graph = Graph.load('./wes_graph.json').graph

    assignment = {node: graph.nodes[node][plan] for node in graph.nodes}

    updaters = {
        **votes_updaters(['VoteA', 'VoteB']),
        'population': Tally('POP100', alias='population'),
        'perimeters': perimeters,
        'exterior_boundaries': exterior_boundaries,
        'interior_boundaries': interior_boundaries,
        'boundary_nodes': boundary_nodes,
        'cut_edges': cut_edges,
        'areas': Tally('utm_area', alias='areas'),
        'polsby_popper': polsby_popper,
        'cut_edges_by_part': cut_edges_by_part
    }

    partition = Partition(graph, assignment, updaters)

    scores = {
        'Mean-Median': functools.partial(mean_median, proportion_column_name='VoteA%'),
        'Mean-Thirdian': functools.partial(mean_thirdian, proportion_column_name='VoteA%'),
        'Efficiency Gap': functools.partial(efficiency_gap, col1='VoteA', col2='VoteB'),
    }

    initial_scores = {key: score(partition)
                      for key, score in scores.items()}

    chain = BasicChain(partition, total_steps=1000000)

    table = pipe_to_table(chain, scores)

    return {key: p_value_report(key, table[key], initial_scores[key]) for key in scores}


if __name__ == '__main__':
    pprint.pprint(run_pa())
