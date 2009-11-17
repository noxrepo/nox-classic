#!/usr/bin/python
#
# TARP
# 5/14/08
# Extracting graphing elements from performance.py, cleaner and nicer, etc.
#
#
# This is 3x as many lines of code as the original graph function
# The price you pay for general/global/modular/assertive whatnots?
#

from utilities import color_generator, Notary
from pylab import plot, plot_date, bar

class PlotLine:
    def __init__(self, x=[], y=[], y_err=[], color=(0,0,0), \
                 label="", style="-", box=False):
        self.args = []
        self.kwargs = {}
        self.e_args = []
        self.e_kwargs = {}

        self.x = x
        self.y = y
        self.y_err = y_err
        self.color = color #? Where is this used?
        self.label = label
        self.style = style
        self.box = box

# Nearly by accident, this makes almost no reference to anything in points
# All that must be provided is:
#  1) A get('name') function for the in/dependent variables
#  2) Something to satisfy --> point_type = point.matches(search) <--
#     that distinguishes between different matching classes
#  3) The str_graph_[fixed | used | ignored] functions, gives a string
#     to put around the graph as background information.

from pylab import errorbar

class Grapher:
    fig_x_grow = 1
    fig_y_grow = 1
    fig_left = .1
    fig_bottom = .1
    fig_right = .7
    fig_top = .85

    bar_buffer = 2
    bar_holes = False
    bar_errorcolor = '#000000'
    bar_drawabove = 'True'

    legend_unit_height = 1./14
    legend_pad = .05

    notary = Notary() # Has no log file of its own
    note = notary.note # This is a function

    def __init__(self, points=[], image_dst=""):
        self.search = None
        self.selected = {}
        self.independent = ""
        self.dependent = ""
        self.plot_func = None
        self.graph_plot = None

        self.error_fmt = None

        self.legend_textsize = 'x-small'
        self.legend_x = .72
        self.legend_y = .2

        self.lines = {}
        self.labels = []

        self.bar_width = 0
        self.x_index = {}
        self.type_index = {}
        self.num_x = 0
        self.num_types = 0
        self.ticks = []
        self.names = []

        self.plots = []

        self.points = points
        self.image_dst = image_dst
        self.error_func = errorbar  # This cannot be outside of init...?

    def locate(self, search):
        selected = {}
        for point in self.points:
            point_type = point.matches(search)
            if point_type:
                if point_type not in selected.keys():
                    selected[point_type] = []
                selected[point_type].append(point)
        self.selected = selected
        self.search = search
        return selected

    def graph(self, independent, dependent, search):
        # All these 'assert's are to show dependencies, there isn't
        # really a way to mess it up if this function (graph) is used,
        # but allows for further graphing-styled functions to be cobbled
        # together later
        #? On the other hand, many of these 'functions' are only executed
        # once, with no arguments, and do not consist of many lines of
        # code.  The problem is that the graphing process is verbose and
        # kind of beastly.
        if not self.points:
            return self.display_fail("No data to graph from")
        # Continuous dependent variable (or non-existant for calculated)
        #? TODO?: Add support for True/False by mapping to 1-0, relabeling
        for point in self.points:
            assert type(point.get(dependent)) in (float, int, type(None)), \
                   "Non-continuous (%s) dependent variable" % \
                   type(point.get(dependent))

#        print "Graphing ... %s, %s" % (dependent, independent)
#        print " None => No preference"
#        print " False => Not considered"
#        print " True => Independent variable"
#        print "Looking for:"
#        print search

        self.independent = independent
        self.dependent = dependent

        self.determine_plot_type()
        assert self.plot_func

        self.note("Graph Type: %s" % (self.plot_func))

        self.locate(search)
        if not self.selected:
            return self.display_fail(
                "0/%d points match criteria" % len(self.points))

        self.note("Found %d matching style%s:\n" \
             % (len(self.selected), (len(self.selected) != 1) and "s" or ""))
        self.display_settings()
        self.setup_figure()
        assert self.graph_plot

        self.generate_lines()
        assert self.lines and self.labels and self.num_x and self.num_types
        assert self.x_index and self.type_index
        if self.plot_func == bar:
            assert self.bar_width

        self.setup_plot()
        for line in self.lines.values():
            assert line.args and line.kwargs and line.e_args and line.e_kwargs

        self.plot_lines()
        assert self.plots

        self.display_finish()

    def plot_lines(self):
        from pylab import xticks, xlim

        assert self.lines
        for line in self.lines.values():
            assert line.args and line.kwargs and line.e_args and line.e_kwargs

        # A little trickery to get a representative plot per type
        # Note that the execution takes place here
        self.plots = {}
        for line_type in self.lines.keys():
            line = self.lines[line_type]
            self.plots[line_type] = self.plot_func(*line.args,**line.kwargs)
            self.error_func(*line.e_args,**line.e_kwargs)
        for p in self.plots:
            self.plots[p] = self.plots[p][0]
        self.plots = self.plots.values()

        if self.plot_func == bar:
            assert len(self.ticks) > 0
            assert self.names
            xticks(self.ticks, self.names)

            x_border = self.bar_width
            x_begin = 0
            if self.bar_holes:
                x_end = len(self.ticks)
            else:
                points = 2*(self.num_x - 1)
                for line_type in self.lines:
                    points += len(self.lines[line_type].x)
                x_end = points*self.bar_width
            xlim(x_begin - x_border, x_end + x_border)
        return self.plots

    def setup_figure(self):
        from pylab import xlabel, ylabel, title, subplot, subplots_adjust

        assert self.fig_x_grow
        assert self.fig_y_grow
        assert self.fig_left
        assert self.fig_bottom
        assert self.fig_right
        assert self.fig_top
        assert self.independent
        assert self.dependent

        graph_plot = subplot(111)
        graph_plot.figure.set_figwidth( \
            graph_plot.figure.get_figwidth() + self.fig_x_grow)
        graph_plot.figure.set_figheight( \
            graph_plot.figure.get_figheight() + self.fig_y_grow)
        subplots_adjust(self.fig_left, self.fig_bottom, \
                        self.fig_right, self.fig_top)
        xlabel(self.independent)
        ylabel(self.dependent)

        title('"%s" with respect to "%s"' % (self.dependent, self.independent))
        self.graph_plot = graph_plot
        return graph_plot

    def setup_plot(self):
        assert self.lines
        assert self.plot_func
        assert self.independent
        assert self.graph_plot
        assert self.num_x
        assert self.num_types
        assert self.x_index
        assert self.type_index
        if self.plot_func == bar:
            assert self.bar_width
            assert self.bar_buffer

        #? Verify below claim
        # Since the legend cannot be v-centered(?), we estimate its proper
        # position and move the bottom of its bounding box
        assert self.legend_unit_height
        self.legend_y = .5 - self.legend_unit_height*self.num_types/2
        if self.legend_y < 0:
            self.note("Selected data may have legend > image",'shallow')
            self.note("** Consider limiting your search, " \
                  "%d classifications is sizable" % self.num_types,'shallow')
            self.legend_y = .01
            #! This is never stated elsewhere besides initializer,
            # so can't re-use grapher without explicitly resetting to a
            # more natural size :(
            self.legend_textsize = 'xx-small'
            self.graph_plot.figure.set_figheight( \
                self.graph_plot.figure.get_figheight() + self.fig_y_grow)

        if self.plot_func == bar:
            from pylab import arange, array
            # Float part is necessary
            ticks = arange(self.num_x, dtype='float')
            # Whether to leave placeholders for bars that do not
            # exist for all possible independent variables:
            # for example, 'pynoop' in 'default' would have a space
            # reserved for it, though no data would be there
            # Causes all sections to take the same amount of space, rather
            # than expanding to fill 'naturally'
            if self.bar_holes:
                for line_type in self.lines.keys():
                    #? This is actually constant with all
                    line = self.lines[line_type]

                    #? Differs
                    slots = []
                    for x in line.x:
                        slots.append(self.x_index[x])

                    #? Should this be in the for-loop perhaps?
                    #? And what is num_type?  self.num_types?
                    ticks[self.x_index[x]] += self.bar_width/2.*num_type
                    slots = array(slots, dtype='float')

                    line.args =[slots+self.type_index[line_type]* \
                                self.bar_width, line.y]
                    line.e_args =[slots+(self.type_index[line_type]+.5)* \
                                  self.bar_width, line.y]

                    #? This is actually constant with all
                    line.kwargs = {'color': line.color, 'label':line.label}
                    line.e_kwargs = {'ecolor': line.color, 'yerr': line.y_err}

            else: # consolidated bar plot, bar_buffer space between each
                # Being careful of rounding errors, range using ints
                bars = range(0,self.num_x*self.bar_buffer,self.bar_buffer)

                #! Could this be done at the end?
                for i in range(0,self.num_x):
                    bars[i] *= self.bar_width

                # 'bars' has been spaced properly, have 'ticks' hold those
                # spaces during the loop
                ticks = bars[:]

                # I know this loop is awful
                x_slots = {}
                x_vals = self.x_index.keys()
                x_vals.sort()
                for x_val in x_vals:
                    for line_type in self.lines.keys():
                        line = self.lines[line_type]
                        if line_type not in x_slots.keys():
                            x_slots[line_type] = []
                        for x in line.x:
                            if x != x_val:
                                continue
                            x_slots[line_type].append(bars[self.x_index[x]])
                            # Slide all following plots up accordingly
                            for i in range(self.x_index[x],len(bars)):
                                #! If the scaling done at the end, this
                                #! would change to just be '+= 1'
                                bars[i] += self.bar_width

                # Temporary prepend to make loop clearer
                ticks = [0] + ticks
                bars = [0] + bars
                #! Document this!
                # This places the ticks in the middle of each of the
                # sections of bars
                for i in range(1,len(bars)):
                    ticks[-i] = (bars[-i]+bars[-i-1]+ticks[-i]-ticks[-i-1])/2
                # Temporary addition removed
                ticks = ticks[1:]
                # Don't use bars anymore, so don't need to remove this
                # in theory, would be confusing and required
                # documentation (much like this) otherwise
                bars = bars[1:]

                for line_type in self.lines.keys():
                    #? This is actually constant with all
                    line = self.lines[line_type]

                    #? Differs
                    slots = array(x_slots[line_type], dtype='float')
                    line.args = [slots, line.y]
                    line.e_args = [slots+.5*self.bar_width, line.y]

                    #? This is actually constant with all
                    line.kwargs = {'color': line.color, 'label':line.label}
                    line.e_kwargs = {'ecolor': line.color, 'yerr': line.y_err}

        else: # Non-bar graph
            for line_type in self.lines.keys():
                #? This is actually constant with all
                line = self.lines[line_type]

                #? Differs
                line.args = [line.x, line.y]
                line.e_args = [line.x, line.y]

                #? This is actually constant with all
                line.kwargs = {'color': line.color, 'label':line.label}
                line.e_kwargs = {'ecolor': line.color, 'yerr': line.y_err}

        # General arguments for all lines
        x_args = []
        x_e_args = []
        x_kwargs = {}
        x_e_kwargs = {'fmt': self.error_fmt}

        # General arguments for some lines
        # Date Plots
        if self.plot_func == plot_date:
            x_kwargs['ls'] = '-'

            self.graph_plot.figure.autofmt_xdate()

        # Bar Charts
        elif self.plot_func == bar:
            assert self.bar_errorcolor
            assert self.bar_drawabove


            x_kwargs['width'] = self.bar_width
            x_e_kwargs['ecolor'] = self.bar_errorcolor
            # 'capsize' is how wide in pixels the caps on the error bar are
            #! This is just a best-guess, in reality, should use:
            # width * [cap width factor] = number value of cap
            #       / [range of x-axis] = screen value
            #       * [width of subplot on screen] = scaled value
            #       * [dots per inch] = pixel width value
            x_e_kwargs['capsize'] = self.bar_width * 2/3 * \
                                    self.graph_plot.figure.get_dpi()
            x_e_kwargs['barsabove'] = self.bar_drawabove

            # Could just use x_index.keys() if we trusted order
            names = [str(self.x_index[x])+str(x) for x in self.x_index.keys()]
            names.sort()
            names = [name[1:] for name in names]

            # Here's where all that work for ticks gets actually placed
            # could have the first line be above
            self.ticks = ticks
            self.names = names

        # Standard Plots
        elif self.plot_func == plot:
            x_kwargs['ls'] = '-'

        else:
            assert 0, "Invalid plot function %s" % self.plot_func

        for line in self.lines.values():
            line.args.extend(x_args)
            line.e_args.extend(x_e_args)
            for kw in x_kwargs:
                line.kwargs[kw] = x_kwargs[kw]
            for kw in x_e_kwargs:
                line.e_kwargs[kw] = x_e_kwargs[kw]

        return self.lines

    def generate_lines(self):
        from pylab import mean, std

        lines = {}
        color = color_generator()
        ind = self.independent
        dep = self.dependent
        labels = []
        for point_type in self.selected:
            x_dict = {}
            for data in self.selected[point_type]:
                if data.get(ind) not in x_dict.keys():
                    x_dict[data.get(ind)] = []
                x_dict[data.get(ind)].append(data.get(dep))

            x = x_dict.keys()
            # Faster to do this with initialized arrays and indicies?
            x.sort() #? Maybe
            y = []
            y_err = []
            # I don't understand why dict[val] would ever be none...
            # also it never broke when actual data was collected
            # part of the problem might be pgen being broken
            for x_val in x:
                #! Bugfix - 'None' value shows up here?  Can't .get
                # the value properly, means poorly passed arguments
                if (None in x_dict[x_val]):
                    self.note("None-values for %s: %s" \
                               % (x_val, x_dict[x_val]), 'error')
                    x_dict[x_val] = [v for v in x_dict[x_val] if v != None]
                    if not x_dict[x_val]:
                        y.append(0)
                        y_err.append(0)
                        continue

                y.append(mean(x_dict[x_val]))

                if len(x_dict[x_val]) > 1:
                    y_err.append(std(x_dict[x_val]))
                else:
                    # could change color as well
                    y_err.append(0) #! Would prefer infinite... consider yaxis
                                    #  though suspicion that it would
                                    #  just auto-scale it back into the
                                    #  screen, requiring manual settings

            deleted = 0
            for i in range(len(x)):
                if not x_dict[x[i-deleted]]:
                    del x[i-deleted]
                    del y[i-deleted]
                    del y_err[i-deleted]
                    deleted += 1
            if not x:
                continue

            # Fatherless dogs error on tuples for barplots, make it hex-color
            value = color.next()
            line_color = '#%02x%02x%02x' % (int(value[0]*256),
                                            int(value[1]*256),
                                            int(value[2]*256))
            lines[point_type] = PlotLine(x ,y, y_err, line_color,
                                         self.label_type(point_type))
            labels.append(self.label_type(point_type))

        num_x = 0
        x_index = {}
        num_types = 0
        type_index = {}

        for line_type in lines.keys():
            line = lines[line_type]
            for x in line.x:
                if x not in x_index.keys():
                    x_index[x] = num_x
                    num_x += 1
                if line_type not in type_index.keys():
                    type_index[line_type] = num_types
                    num_types += 1

        if self.plot_func == bar:
            self.bar_width = 1./(num_types + self.bar_buffer)

        self.num_x = num_x
        self.num_types = num_types
        self.x_index = x_index
        self.type_index = type_index

        self.labels = labels
        self.lines = lines
        return lines

    # Given an initial list (which may contain strings, ints, classes,
    # dicts, or lists itself) concatenate strings in a depth-first manner,
    # printing nothing for 'None' items
    # In this code the 'list' is the search result from 'point.matches(~)',
    # or a sub-item of the original result.
    # Example:
    #! TODO
    def label_type(self, items):
        label = ""
        for item in items:
           if item == None:
              pass
           elif type(item) == str:
               label += item + "\n"
           else:
               try:
                   label += self.label_type(item)
               except TypeError:
                   label += str(item) + "\n"
        return label

    def determine_plot_type(self):
        self.plot_type = None
        if 'date' in self.independent:  #! Another specific statement
            self.plot_func = plot_date
        else:
            for point in self.points:
                if point.get(self.independent) == None:
                    continue
                if type(point.get(self.independent)) == str:
                    self.plot_func = bar
                else:
                    self.plot_func = plot
        if self.plot_func == None:
            self.note("No points found with values for %s" \
                      % self.independent, "error")
        return self.plot_func

    def display_fail(self, message):
        #? If there is a way to stretch this an inch as well, it would
        # help with text overlap.  not sure if it is possible without
        # making a subplot, and corresponding strange boxes
        from pylab import savefig, close, axes, figtext

        axes([0,0,.01,.01])
        figtext(.5, .5, message, ha='center',va='center',size='x-large')
        self.display_settings()
        savefig(self.image_dst + ".png")
        close()
        return False

    def display_settings(self):
        from pylab import figtext
        assert self.search

        search = self.search
        figtext(.01,.99,search.str_graph_fixed(), va='top',fontsize='medium')
        figtext(.35, .99, search.str_graph_used(), va='top',fontsize='medium')
        #? Perhaps remove ignored variables during streamlining, the
        # reason they are ignored is that no one cares - also implied
        # from the values in the first two ...
        #figtext(.6, .99, search.str_graph_ignored(),va='top',fontsize='medium')

    def display_finish(self):
        from pylab import savefig, close, legend
        from matplotlib import font_manager

        assert self.graph_plot
        assert self.plots
        assert self.labels
        assert self.legend_x
        assert self.legend_y
        assert self.legend_pad
        assert self.legend_textsize
        assert self.image_dst

        self.graph_plot.figure.legend(tuple(self.plots),tuple(self.labels),\
                loc=(self.legend_x,self.legend_y), pad=self.legend_pad, \
                prop=font_manager.FontProperties(size=self.legend_textsize))
        savefig(self.image_dst + ".png")
        close()

    # Stripped this out of the 'if bar' clauses for the original graph
    # function, just goes to show how the 'line' concept is less useful
    # when doing a bar graph - this plus a few starter/stopper functions
    # does the work of many lines of code above
    def old_bar_graph_WOULD_NEED_FIX(
           img_dst, points, independent, dependent, search):
        from pylab import arange, xticks, xlim, mean, std
        # Lines
        plots = []
        labels = []
        args = {}
        for point in points:
            args[point.get(independent)] = True
        keys = args.keys()
        keys.sort()
        ind = {}
        bars = {}
        for k in keys:
            ind[k] = keys.index(k)
            bars[k] = {}
        # Float is necessary
        ticks = arange(len(args), dtype='float')

        for point_type in selected:
            x_val = []
            y_val = []
            for point in selected[point_type]:
                x_val.append(point.get(independent))
                y_val.append(point.get(dependent))

            width = 1./(len(selected)+2)
            for point in selected[point_type]:
                pi = point.get(independent)
                pd = point.get(dependent)
                # bars[independent][screen] = ([points],position,color)
                if point_type not in bars[pi].keys():
                    bars[pi][point_type] = ([pd], \
                                            ind[pi]+width*len(bars[pi]), \
                                            color)
                else:
                    bars[pi][point_type][0].append(pd)
            labels.append(label_type(point_type))

        plotlist = {}
        for pi in bars:
            for pt in bars[pi]:
                if len(bars[pi][pt][0]) > 1:
                    error = std(bars[pi][pt][0])
                else:
                    error = 0
                p = bar(bars[pi][pt][1],mean(bars[pi][pt][0]),width,\
                      color=bars[pi][pt][2], yerr=error)
                plotlist[pt] = p
                ticks[ind[pi]] += width/2
        plots = plotlist.values()
        plots.sort()
        keys = args.keys()
        keys.sort()
        xticks(ticks, keys)
        xlim(-width,len(ticks))
