include ../../../Make.vars 

if PY_ENABLED
AM_CPPFLAGS += $(PYTHON_CPPFLAGS)

NOX_PYBUILDFILES = \
	pyjsonmsgevent_wrap.cc \
	pyjsonmsgevent.py

jsonmsg_wrap_includes = \
	jsonmsg_event.i

pyjsonmsgevent_wrap.cc pyjsonmsgevent.py: $(jsonmsg_wrap_includes)
	$(SWIG) $(SWIG_PYTHON_OPT) -I$(top_srcdir)/src/nox/lib/ -I$(top_srcdir)/src/nox/coreapps -outdir $(builddir)/. -o pyjsonmsgevent_wrap.cc -module pyjsonmsgevent $(srcdir)/jsonmsg_event.i
	
_pyjsonmsgevent_la_CPPFLAGS = $(AM_CPPFLAGS) -I$(top_srcdir)/src/nox -I$(srcdir)/../ -I$(top_builddir)/src/nox/ -I$(top_srcdir)/src/nox/coreapps/
_pyjsonmsgevent_la_SOURCES = jsonmessenger.hh
nodist__pyjsonmsgevent_la_SOURCES = pyjsonmsgevent_wrap.cc pyjsonmsgevent.py
_pyjsonmsgevent_la_LDFLAGS = -module

NOX_PYLIBFILES = _pyjsonmsgevent.so 

endif # PY_ENABLED

pkglib_LTLIBRARIES =		\
	messenger_core.la \
	messenger.la \
	jsonmessenger.la \
	jsonmsg_event.la
	
jsonmsg_event_la_CPPFLAGS = $(AM_CPPFLAGS) -I $(top_srcdir)/src/nox
jsonmsg_event_la_SOURCES = jsonmessenger.cc
jsonmsg_event_la_LDFLAGS = -module -export-dynamic
	
if PY_ENABLED
pkglib_LTLIBRARIES += _pyjsonmsgevent.la 
endif # PY_ENABLED

messenger_la_CPPFLAGS = $(AM_CPPFLAGS) -I $(top_srcdir)/src/nox -I $(top_srcdir)/src/nox/coreapps/
messenger_la_SOURCES = messenger.cc messenger.hh
messenger_la_LDFLAGS = -module -export-dynamic

messenger_core_la_CPPFLAGS = $(AM_CPPFLAGS) -I $(top_srcdir)/src/nox -I $(top_srcdir)/src/nox/coreapps/
messenger_core_la_SOURCES = messenger_core.cc messenger_core.hh
messenger_core_la_LDFLAGS = -module -export-dynamic


jsonmessenger_la_CPPFLAGS = $(AM_CPPFLAGS) -I $(top_srcdir)/src/nox -I $(top_srcdir)/src/nox/coreapps/
jsonmessenger_la_SOURCES = jsonmessenger.hh jsonmessenger.cc
jsonmessenger_la_LDFLAGS = -module -export-dynamic

NOX_RUNTIMEFILES = meta.json \
	serverkey.pem \
	cacert.pem \
	servercert.pem \
	messenger.py \
	__init__.py

EXTRA_DIST = \
	serverkey.pem \
	cacert.pem \
	servercert.pem \
	meta.json \
	messenger.py \
	__init__.py 

all-local:  nox-all-local
clean-local: nox-clean-local
install-exec-hook: nox-install-local
