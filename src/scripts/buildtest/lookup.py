#!/usr/bin/python

import matplotlib
matplotlib.use('Agg')

import pickle
import pwd
import os

import info
import graph

def create_image(argv):
        p = info.Profile()
        b = info.Build()
        t = info.Test()
        r = info.Result()

        values = []
        for v in argv[1:]:
            if v == 'True':
                values.append(True)
            elif v == 'False':
                values.append(False)
            elif v == 'None':
                values.append(None)
            else:
                try:
                    values.append(float(v))
                except:
                    values.append(v)

        (p.user, p.machine, p.run_date, \
         b.commit, b.last_author, b.build_date, \
         t.configuration, t.command, t.packets, t.rules, t.policies, \
         r.total, r.user, r.system, ind, dep) = values

        if p.user == p.machine == p.run_date:
            p = p.user
        if b.commit == b.last_author == b.build_date:
            b = b.commit
        if t.configuration == t.command == t.packets == t.rules == t.policies:
            t = t.configuration
        if r.total == r.user == r.system:
            r = r.total
        user = pwd.getpwuid(os.getuid())[0]
        input = '/var/www/buildtest/' + user +'/archive/performance.pkl'
        raw_points = pickle.load(open(input,'r'))

        g = graph.Grapher(raw_points,'librarian')
        search = info.RawData(p, b, t, r)
        print search
        g.graph(ind, dep, search)


if __name__ == "__main__":
    import sys
    create_image(sys.argv)
