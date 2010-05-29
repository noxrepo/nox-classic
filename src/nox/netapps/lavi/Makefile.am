include ../../../Make.vars 

EXTRA_DIST =\
	meta.json

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
endif # PY_ENABLED 

pkglib_LTLIBRARIES =\
	lavi_nodes.la \
	lavi_switches.la \
	lavi.la

lavi_la_CPPFLAGS = $(AM_CPPFLAGS) -I $(top_srcdir)/src/nox -I $(top_srcdir)/src/nox/netapps/
lavi_la_SOURCES = lavi.hh lavi.cc
lavi_la_LDFLAGS = -module -export-dynamic

lavi_nodes_la_CPPFLAGS = $(AM_CPPFLAGS) -I $(top_srcdir)/src/nox -I $(top_srcdir)/src/nox/netapps/ -I $(top_srcdir)/src/nox/coreapps/
lavi_nodes_la_SOURCES = lavi_nodes.hh lavi_nodes.cc
lavi_nodes_la_LDFLAGS = -module -export-dynamic

lavi_switches_la_CPPFLAGS = $(AM_CPPFLAGS) -I $(top_srcdir)/src/nox -I $(top_srcdir)/src/nox/netapps/ -I $(top_srcdir)/src/nox/coreapps/
lavi_switches_la_SOURCES = lavi_switches.hh lavi_switches.cc
lavi_switches_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.json	

all-local: nox-all-local
clean-local: nox-clean-local 
install-exec-hook: nox-install-local
