//
// utf8_string - pass python unicode string parameters to C++ as UTF-8
//               encoded std::string
//
#ifndef SWIG_UTF8_STRING
#define SWIG_UTF8_STRING

%{
#include <string>
%}

%typemap(in) std::string {
    if (PyUnicode_Check($input)) {
        PyObject* strobj = PyUnicode_AsUTF8String($input);
        if (!strobj) {
            PyErr_SetString(PyExc_ValueError,
                    "Failed to decode string as utf-8");
            return NULL;
        }
        $1 = string(PyString_AsString(strobj));
        Py_DECREF(strobj);
    }
    else if PyString_Check($input) {
        $1 = string(PyString_AsString($input));
    }
    else {
        PyErr_SetString(PyExc_ValueError,"Expected a string");
        return NULL;
    }
}

#endif /* ndef SWIG_UTF8_STRING */

