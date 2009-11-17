DOXYGEN = doxygen

PAPER=letter

.PHONY: help clean html latex images


EXTRA_DIST=doxygen.conf.in customdoxygen.css header.html footer.html images

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html      to make HTML files"
	@echo "  latex     to make Latex files, you canset PAPER=a4 or PAPER=letter"

clean:

html:
	rm -rf html
	sed -e 's:^GENERATE_HTML *= NO:GENERATE_HTML = YES:' < doxygen.conf | $(DOXYGEN) -

latex:
	rm -rf latex
	sed -e 's:^GENERATE_LATEX *= NO:GENERATE_LATEX = YES:' -e 's:^PAPER_TYPE *= letter:PAPER_TYPE = $(PAPER):' < doxygen.conf | $(DOXYGEN) -
	(cd latex && make pdf)
