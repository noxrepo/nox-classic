include ../../../Make.vars 

EXTRA_DIST =\
	meta.xml

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
endif # PY_ENABLED 

pkglib_LTLIBRARIES =\
	trackhost_pktin.la \
	hosttracker.la 

hosttracker_la_CPPFLAGS = $(AM_CPPFLAGS) -I $(top_srcdir)/src/nox -I $(top_srcdir)/src/nox/netapps/
hosttracker_la_SOURCES = hosttracker.hh hosttracker.cc
hosttracker_la_LDFLAGS = -module -export-dynamic

trackhost_pktin_la_CPPFLAGS = $(AM_CPPFLAGS) -I $(top_srcdir)/src/nox -I $(top_srcdir)/src/nox/netapps/
trackhost_pktin_la_SOURCES = trackhost_pktin.hh trackhost_pktin.cc
trackhost_pktin_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.xml	

all-local: nox-all-local
clean-local: nox-clean-local 
install-exec-hook: nox-install-local
