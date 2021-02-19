import pathlib 
import networkx as nx
import tempfile 
import os
import sys
import subprocess
import codecs

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

def gml_to_list(path):
    for i in path.glob('**/*.gml'):
        g = nx.read_gml(i)
        dir = pathlib.Path(i).parent.absolute()
        name = i.name.split(".")[0]
        target = pathlib.Path(dir.joinpath(name))
        
        with target.open("w+") as f:
            for (u, v) in g.edges(data=False):
                f.write("{:d} {:d}\n".format(int(u), int(v)))
        i.unlink()
            

def main():
    path = pathlib.Path.cwd().joinpath('test')

    #convert to sif
    for i in path.glob('**/*.*'):
        if i.suffixes[0] == ".gr":
            read_gr(i)   
        elif i.suffixes[0] == ".graph6":
            read_graph6(i)
        elif i.suffixes[0] == ".td":
            i.unlink()

    #check for yoshiko
    solver = pathlib.Path.cwd().joinpath('yoshiko')
    if not os.path.isfile(solver):
        sys.exit("Error: binary not found: " + str(solver))

    #solve and store solution complexity
    optima = pathlib.Path.cwd().joinpath('test', 'optimum.txt')
    with optima.open("w+") as f:
        f.write("<file>\t<complexity>\n")
        for i in path.glob('**/*.sif'):
            #solver cant solve empty files
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
                                    "-o",
                                    gml],
                    stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE)

                try:
                    outs, errs = proc.communicate(timeout=1800)
                    optimality = codecs.decode(outs, 'UTF-8')
                    f.write(name + "\t" + optimality)
                    i.unlink()
                except subprocess.TimeoutExpired:
                    proc.kill()
                    outs, errs = proc.communicate()
                    f.write(name + "\t" + "ERR")
                
                
                
                
    
    gml_to_list(path)
                
            
if __name__ == "__main__":
   main()