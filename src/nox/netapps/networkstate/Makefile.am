include ../../../Make.vars 

EXTRA_DIST =\
	meta.xml

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)
endif # PY_ENABLED 

pkglib_LTLIBRARIES =\
	datapathmem.la

datapathmem_la_CPPFLAGS = $(AM_CPPFLAGS) -I $(top_srcdir)/src/nox -I $(top_srcdir)/src/nox/netapps/
datapathmem_la_SOURCES = datapathmem.hh datapathmem.cc
datapathmem_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.xml	

all-local: nox-all-local
clean-local: nox-clean-local 
install-exec-hook: nox-install-local
