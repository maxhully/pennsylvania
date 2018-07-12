from graphmaker.graph import Graph
from rundmcmc.partition import Partition
from rundmcmc.updaters import (Tally, perimeters, exterior_boundaries,
                               interior_boundaries, boundary_nodes, cut_edges, polsby_popper,
                               cut_edges_by_part)


def test_polsby_popper_between_zero_and_one():
    graph = Graph.load('./PA_queen.json').graph

    assignment = {node: graph.nodes[node]['GOV_4_1'] for node in graph.nodes}

    updaters = {
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

    assert all([0 < value < 1 for value in partition['polsby_popper'].values()])
