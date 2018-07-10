import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import geopandas

from graphmaker.graph import Graph


def corrections_for_islands(graph, column):
    new_assignments = dict()
    for node in graph.nodes:
        value_of_one = graph.nodes[graph.neighbors(node)[0]][column]
        all_neighbors_agree = all(
            graph.nodes[neighbor][column] == value_of_one for neighbor in graph[node])
        if graph.nodes[node] == value_of_one and all_neighbors_agree:
            new_assignments[node] = value_of_one
    return new_assignments


def main(col='CD_CR'):
    pa = Graph.load('wes_graph.json')
    shape = geopandas.read_file('./wes_unitsPA/wes_unitsPA.shp')

    corrections = corrections_for_islands(pa.graph, col)
    for node, new_assignment in corrections.items():
        pa.graph.nodes[node][col] = new_assignment

    pa.save()


if __name__ == '__main__':
    main()
