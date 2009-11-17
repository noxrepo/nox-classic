include ../../../Make.vars 

CONFIGURE_DEPENCIES = $(srcdir)/Makefile.am

EXTRA_DIST =\
	meta.xml

pkglib_LTLIBRARIES =		\
	hub.la

hub_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(top_srcdir)/src/nox
hub_la_SOURCES = hub.cc
hub_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.xml

all-local: nox-all-local
clean-local: nox-clean-local 
install-exec-hook: nox-install-local
