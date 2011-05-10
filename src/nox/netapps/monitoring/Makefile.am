include ../../../Make.vars 

#SUBDIRS = t

EXTRA_DIST =\
	meta.json\
	__init__.py\
	linkutilreplyevent.py\
	switchqueryreplyevent.py\
	porterrorevent.py\
	silentswitchevent.py\
	switchadminupevent.py\
	switchadmindownevent.py\
	linkadminupevent.py\
	linkadmindownevent.py\
	monitoring.py

NOX_RUNTIMEFILES = meta.json	\
	__init__.py		\
	linkutilreplyevent.py\
	switchqueryreplyevent.py\
	porterrorevent.py\
	silentswitchevent.py\
	switchadminupevent.py\
	switchadmindownevent.py\
	linkadminupevent.py\
	linkadmindownevent.py\
	monitoring.py

all-local: nox-all-local
install-exec-hook: nox-install-local
