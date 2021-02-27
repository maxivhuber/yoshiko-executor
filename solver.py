import pathlib
import networkx as nx
import tempfile
import os
import sys
import subprocess
import codecs
import time
import multiprocessing
import csv
from datetime import datetime


def read_gr(file):
    sys.stdout.write(str(file) + '\n')
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
            sys.stderr.write("to many arguments\n")
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
                    sys.stderr.write("expected two number parameter!\n")
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
            else:
                sys.stderr.write("wrong input format!\n")
                return

        else:
            sys.stderr.write("expected meta information on first line!\n")
            return
    else:
        sys.stderr.write("expected exactly one line with\n")
        return


def read_graph6(file):
    sys.stdout.write(str(file) + '\n')
    tmp = tempfile.TemporaryFile()
    content = file.read_text()

    for i in iter(content.splitlines()):
        i = i.strip().split(" ")
        graph6 = i[0]
        g = nx.from_graph6_bytes(bytes(graph6, "UTF-8"))
        for (u, v) in g.edges(data=False):
            tmp.write(bytes("{:d} {:d}\n".format(u + 1, v + 1), "UTF-8"))
    tmp.seek(0)
    to_sif(file, tmp)


def to_sif(file, tmp):
    name = file.name.split(".")[0]
    path = pathlib.Path(file).parent.absolute()
    sif = path.joinpath(name + '.sif')

    with sif.open("w+") as f:
        for i in tmp:
            values = codecs.decode(i, "UTF-8").rstrip().split(" ")
            f.write("{:d} xx {:d}\n".format(int(values[0]), int(values[1])))


def gml_to_list(path):
    for i in path.glob('**/*.gml'):
        g = nx.read_gml(i)
        dir = pathlib.Path(i).parent.absolute()
        name = i.name.split(".")[0]
        target = pathlib.Path(dir.joinpath(name))

        with target.open("w+") as f:
            for (u, v) in g.edges(data=False):
                f.write("{} {}\n".format(u, v))
        i.unlink()


def main():
    path = pathlib.Path.cwd().joinpath('test')

    # convert to sif
    for i in path.glob('**/*.*'):
        if i.suffixes[0] == ".gr":
            read_gr(i)
        elif i.suffixes[0] == ".graph6":
            read_graph6(i)
        elif i.suffixes[0] == ".td":
            i.unlink()

    # check for yoshiko
    solver = pathlib.Path.cwd().joinpath('yoshiko')
    if not os.path.isfile(solver):
        sys.exit("Error: binary not found: " + str(solver))

    # solve and store solution complexity
    optima = pathlib.Path.cwd().joinpath('test', 'optimum.csv')
    with open(optima, 'w') as f:
        header = ['filename', 'seconds', 'complexity']
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()

        cpu = multiprocessing.cpu_count() - 2
        for i in path.glob('**/*.sif'):
            # solver cant solve empty files
            if os.stat(i).st_size == 0:
                i.unlink()
            else:
                dir = pathlib.Path(i).parent.absolute()
                name = i.name.split(".")[0]
                gml = dir.joinpath(name)
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
                                         gml],
                                        stdout=subprocess.PIPE,
                                        stdin=subprocess.PIPE)

                try:
                    start = time.time()
                    outs, errs = proc.communicate(timeout=1800)
                    end = time.time()

                    complexity = codecs.decode(outs, 'UTF-8')
                    elapsed = end - start
                    writer.writerow({'filename': name.strip(),
                                     'seconds': elapsed,
                                     'complexity': complexity.strip()})
                    i.unlink()
                except subprocess.TimeoutExpired:
                    proc.kill()
                    writer.writerow({'filename': name.strip(),
                                     'seconds': "Err",
                                     'complexity': "Err"})

    gml_to_list(path)


if __name__ == "__main__":
    main()
