import pathlib 
import networkx as nx
import tempfile 

def read_gr(file):
    tmp = tempfile.TemporaryFile(mode = 'w+')
    content = file.read_text()

    #expected vertices n and edges m
    exp_n = -1
    exp_m = -1
    
    for i in iter(content.splitlines()):
        try:
            if i[0] == 'p':
                x = i.split(" ")
                if len(x) == 4:
                    exp_n = int(x[2])
                    exp_m = int(x[3])
                else:
                    return
        except:
            return

    g = nx.Graph()
    for i in iter(content.splitlines()):
        if i.strip().replace(" ", "").isnumeric():
            x = i.split()
            if len(x) == 2:
                g.add_edge(x[0], x[1])
            else:
                return
    #vertices n and edges m
    n = g.order()
    m = g.size()

    for (u, v) in g.edges(data=False):
        tmp.write("{:d} {:d}\n".format(int(u), int(v)))

    tmp.seek(0)

    if n == exp_n and not 0 and m == exp_m and not 0 or n < exp_n and m == exp_m: 
    #only if valid
        to_sif(file, tmp)

def read_graph6(file):
    tmp = tempfile.TemporaryFile(mode = 'w+')
    content = file.read_text()

    for i in iter(content.splitlines()):
        i = i.strip().split(" ")
        graph6 = i[0]
        g = nx.from_graph6_bytes(bytes(graph6, "utf-8"))
        for (u, v) in g.edges(data=False):
                tmp.write("{:d} {:d}\n".format(u + 1, v + 1))
    tmp.seek(0)
    to_sif(file, tmp)

def to_sif(file, tmp):
    name = file.name.split(".")[0]
    path = pathlib.Path(file).parent.absolute()
    sif = path.joinpath(name + '.sif')

    with sif.open("w+") as f:
        for i in tmp:
            values = i.rstrip().split(" ")
            f.write("{:d} xx {:d}\n".format(int(values[0]), int(values[1])))


def main():
    path = pathlib.Path.cwd().joinpath('test')

    for i in path.glob('**/*.*'):
        if i.suffixes[0] == ".gr":
            read_gr(i)   
        elif i.suffixes[0] == ".graph6":
            read_graph6(i)
        elif i.suffixes[0] == ".td":
            i.unlink()

if __name__ == "__main__":
   main()