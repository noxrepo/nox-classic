include ../../../Make.vars 

EXTRA_DIST =\
	meta.json\
        __init__.py \
	spanning_tree.py

NOX_RUNTIMEFILES = meta.json	\
        __init__.py \
	spanning_tree.py

all-local: 
	@dlist="$(NOX_RUNTIMEFILES)";for f in $$dlist; do \
	  if test -f $(srcdir)/$$f && test ! -f $$f; then \
		ln -sf $(srcdir)/$$f $(builddir)/$$f;\
	  fi;\
	done; 
