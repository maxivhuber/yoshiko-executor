import pathlib
import networkx as nx
import pygraphviz as pgv
import tempfile
import sys
import subprocess
import codecs
import time
import multiprocessing
import csv
from datetime import datetime


def read_gr(file):
    tmp = tempfile.NamedTemporaryFile()
    description = []
    # remove comments save graph description
    with open(file) as f:
        content = f.read().rstrip().splitlines()
        for line in content:
            if line[0] == 'p':
                description.append(line)
            if not line[0] == 'c':
                tmp.write(bytes(line + '\n', "UTF-8"))

    # read count of vertices and edges (must be first non commeted line)
    tmp.seek(0)
    g = nx.Graph()
    if len(description) == 1:
        info = codecs.decode(tmp.readline().strip(), "UTF-8").split(" ")
        if len(info) > 4:
            sys.stderr.write("to many arguments: {}\n".format(str(file)))
            return
        if info[0] == 'p' and info[2].isnumeric() and info[3].isnumeric():
            r_vertices = int(info[2])
            r_edges = int(info[3])
            # read remaining edges and build graph
            for i in tmp:
                edge = codecs.decode(i, "UTF-8").split()
                if len(edge) == 2 and edge[0].isnumeric() and edge[1].isnumeric():
                    g.add_edge(edge[0], edge[1])
                else:
                    sys.stderr.write(
                        "expected two number parameter: {}\n".format(str(file)))
                    return

            b_vertices = g.number_of_nodes()
            b_edges = g.number_of_edges()

            if r_vertices == b_vertices and r_edges == b_edges or r_vertices > b_vertices and r_edges == b_edges:
                tmp.seek(0)
                tmp.truncate(0)

                for (u, v) in g.edges(data=False):
                    tmp.write(
                        bytes("{:d} {:d}\n".format(int(u), int(v)), "UTF-8"))

                tmp.seek(0)
                to_sif(file, tmp)

                # return initial graph to caller
                return g
            else:
                sys.stderr.write("wrong input format: {}\n".format(str(file)))
                return

        else:
            sys.stderr.write(
                "expected meta information on first line: {}\n".format(str(file)))
            return
    else:
        sys.stderr.write(
            "expected exactly one line with: {}\n".format(str(file)))
        return


def read_graph6(file):
    tmp = tempfile.NamedTemporaryFile()
    content = file.read_text()

    for i in iter(content.splitlines()):
        i = i.strip().split(" ")
        graph6 = i[0]
        g = nx.from_graph6_bytes(bytes(graph6, "UTF-8"))
        for (u, v) in g.edges(data=False):
            tmp.write(bytes("{:d} {:d}\n".format(u + 1, v + 1), "UTF-8"))
    tmp.seek(0)

    g = nx.read_edgelist(tmp.name)
    tmp.seek(0)
    to_sif(file, tmp)

    # return initial graph to caller
    return g


def to_sif(file, tmp):
    name = file.name.split(".")[0]
    path = pathlib.Path(file).parent.absolute()
    solution = path.joinpath(name)

    # dont create .sif file if solution file already exists
    if(not solution.exists()):
        sif = path.joinpath(name + '.sif')

        with sif.open("w+") as f:
            for i in tmp:
                values = codecs.decode(i, "UTF-8").rstrip().split(" ")
                f.write("{:d} xx {:d}\n".format(
                    int(values[0]), int(values[1])))


def gml_to_list(path):
    for i in path.glob('**/*.gml'):
        g = nx.read_gml(i)
        dir = pathlib.Path(i).parent.absolute()
        name = i.name.split(".")[0]
        target = pathlib.Path(dir.joinpath(name))
        img = pathlib.Path(dir.joinpath(name + "_solution.png"))
        graph_writer(g, img)

        with target.open("w+") as f:
            for (u, v) in g.edges(data=False):
                f.write("{} {}\n".format(u, v))
        i.unlink()


def get_characteristics(graph):
    n_vertices = graph.number_of_nodes()
    n_edges = graph.number_of_edges()
    n_components = nx.number_connected_components(graph)
    return (n_vertices, n_edges, n_components)


def graph_writer(graph, path):
    G = nx.nx_agraph.to_agraph(graph)
    G.draw(path, format="png", prog="fdp")


def main():

    # check for yoshiko
    solver = pathlib.Path.cwd().joinpath('yoshiko')
    if not solver.is_file():
        sys.exit("Err: binary not found: " + str(solver))

    path = pathlib.Path.cwd().joinpath('test')
    graphs = {}

    # search for .gr and .graph6 files and convert to .sif
    for i in path.glob('**/*.*'):
        if i.suffix == ".gr":
            g = read_gr(i)
            if isinstance(g, nx.classes.graph.Graph):
                graphs.update({str(i.with_suffix('')): g})
                # plot initial graph from .gr
                dir = pathlib.Path(i).parent.absolute()
                name = i.name.split(".")[0]
                target = pathlib.Path(dir.joinpath(name + '_initial.png'))
                if not target.exists():
                    graph_writer(g, target)

        elif i.suffix == ".graph6":
            g = read_graph6(i)
            if isinstance(g, nx.classes.graph.Graph):
                graphs.update({str(i.with_suffix('')): g})
                # plot initial graph from .graph6
                dir = pathlib.Path(i).parent.absolute()
                name = i.name.split(".")[0]
                target = pathlib.Path(dir.joinpath(name + '_initial.png'))
                if not target.exists():
                    graph_writer(g, target)

        elif i.suffix == ".td":
            i.unlink()

    # solve and store important characteristics
    optima = pathlib.Path.cwd().joinpath('test', 'optimum.csv')
    if not optima.exists():
        optima.touch()
    with open(optima, 'a+') as f:
        header = ['filename', 'n', 'k',
                  'G(initial) = (V, E)', 'G(solution) = (V, E)', 'Components']
        writer = csv.DictWriter(f, fieldnames=header)

        if (optima.stat().st_size == 0):
            writer.writeheader()

        cpu = multiprocessing.cpu_count() - 2

        # solve earlier created .sif files
        for i in path.glob('**/*.sif'):
            # solver cant solve empty files
            if i.stat().st_size == 0:
                i.unlink()
            else:
                sys.stdout.write("solving: {}\n".format(str(i)))
                dir = pathlib.Path(i).parent.absolute()
                name = i.name.split(".")[0]

                # as String: Key to dict "graphs"
                # as Pathlib.path: Path to yoshiko solution
                solution = dir.joinpath(name)
                # path to solution file
                gml = solution.with_suffix('.gml')

                proc = subprocess.Popen([solver,
                                         "-f",
                                         i,
                                         "-F",
                                         str(1),
                                         "-O",
                                         str(2),
                                         "-v",
                                         str(1),
                                         "-threads",
                                         str(cpu),
                                         "-o",
                                         solution],
                                        stdout=subprocess.PIPE,
                                        stdin=subprocess.PIPE)

                try:
                    start = time.time()
                    outs, errs = proc.communicate(timeout=1800)
                    end = time.time()

                    # "solution" points now to graph in dict
                    graph_init = graphs.get(str(solution))
                    ig = get_characteristics(graph_init)

                    # "gml" points to solution file
                    graph_sol = nx.read_gml(gml)
                    og = get_characteristics(graph_sol)

                    complexity = codecs.decode(outs, 'UTF-8')
                    elapsed = end - start
                    writer.writerow({'filename': name.strip(),
                                     'n': elapsed,
                                     'k': complexity.strip(),
                                     'G(initial) = (V, E)': 'G = ({}, {})'.format(ig[0], ig[1]),
                                     'G(solution) = (V, E)': 'G = ({}, {})'.format(og[0], og[1]),
                                     'Components': og[2]})
                    i.unlink()

                except subprocess.TimeoutExpired:
                    proc.kill()
                    graph_init = graphs.get(str(solution))
                    ig = get_characteristics(graph_init)
                    writer.writerow({'filename': name.strip(),
                                     'n': "Err",
                                     'k': "Err",
                                     'G(initial) = (V, E)': 'G = ({}, {})'.format(ig[0], ig[1]),
                                     'G(solution) = (V, E)': 'Err',
                                     'Components': ig[2]})
                    i.unlink()
    gml_to_list(path)


if __name__ == "__main__":
    main()
