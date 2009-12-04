/** \page Howto Basic howto and Convenient Tools in NOX
 * <UL>
 * <LI> \ref new-c-component </LI>
 * </UL>
 * 
 * \section new-c-component Creating new C/C++ component
 * @author ykk
 * @date December 2009
 *
 * To create a new C/C++ component, the following has to be done:
 * <OL>
 * <LI>Create a new directory in coreapps, netapps or webapps</LI>
 * <LI>Add the appropriate C and header files with meta.xml and Makefile.am</LI>
 * <LI>Add the new directory to configure.ac.in</LI>
 * <LI>Rerun ./boot.sh and ./configure<LI>
 * </OL>
 * A sample of the files needed in step 2 is given in coreapps/simple_c_app.
 * nox-new-c-app.py is a script that uses coreapps/simpe_c_app to create a 
 * new C/C++ component (executing step 1 to 3).  The script takes in the new
 * component's name, and has to be run in coreapps, netapps or webapps.
 *
 */
